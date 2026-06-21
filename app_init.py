"""
app_init.py
Fonctions d'initialisation de l'application
"""

import os
from pathlib import Path
import streamlit as st
from core.rag import DocumentExtractor
from core.memory import Memory
from core.parser import GameState
from core.characters import CharacterManager
from core.utils import load_config

# Charger HF_TOKEN depuis .env si présent
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def init_app():
    """Initialise l'application"""
    st.set_page_config(
        page_title="MJ - Les Lames du Cardinal",
        page_icon="🗡️",
        layout="wide"
    )

    # Charger la config
    config_path = Path("config.yaml")
    if not config_path.exists():
        st.error("❌ Fichier config.yaml non trouvé!")
        st.info("Crée un fichier config.yaml à la racine du projet.")
        st.stop()

    config = load_config(config_path)

    # Créer la structure de répertoires
    for path in config['paths'].values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)

    # Démarrer Ollama si nécessaire
    from core.utils import ensure_ollama_running, validate_ollama_installation
    if not validate_ollama_installation():
        st.warning("⚠️ Ollama ne semble pas installé ou accessible.")
    elif not ensure_ollama_running():
        st.error("❌ Impossible de démarrer Ollama. Vérifie ton installation.")
    else:
        # Déjà prêt ou vient d'être démarré — rien à signaler
        pass

    return config


def load_system_prompt():
    """Charge les instructions système depuis system_prompt.txt"""
    prompt_path = Path("system_prompt.txt")
    if not prompt_path.exists():
        return ""
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_prompt(config: dict, key: str) -> str:
    """Charge un prompt depuis prompts/<file> ; fallback sur config.yaml si absent."""
    prompts_cfg = config.get('prompts', {})
    file_key = key + '_file'
    filename = prompts_cfg.get(file_key)
    if filename:
        prompts_dir = Path(prompts_cfg.get('prompts_dir', 'prompts'))
        prompt_path = prompts_dir / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
    return prompts_cfg.get(key, '')


def init_session_state(config):
    """Initialise le session state"""
    if 'initialized' not in st.session_state:
        # Configuration
        st.session_state.config = config

        # Chemins
        paths = config['paths']
        st.session_state.memory_dir = paths['memory_dir']
        st.session_state.char_dir = paths['char_dir']
        st.session_state.db_dir = paths['db_dir']
        st.session_state.pdf_root = paths['pdf_root']

        # Mémoire
        mj_file = paths['memory_dir'] / "mj_memory.json"
        encyclo_file = paths['memory_dir'] / "encyclo_memory.json"

        st.session_state.mj_memory = Memory(
            max_size=config['memory']['max_mj_memory'],
            memory_file=mj_file
        )
        st.session_state.encyclo_memory = Memory(
            max_size=config['memory']['max_encyclo_memory'],
            memory_file=encyclo_file
        )

        # État du jeu
        st.session_state.game_state = GameState()

        # Timeline
        st.session_state.timeline = []

        # Statistiques
        if config['advanced'].get('enable_statistics', True):
            from core.memory import Statistics
            st.session_state.statistics = Statistics()

        # Sessions
        from core.memory import SessionManager
        st.session_state.session_manager = SessionManager(paths['save_dir'])

        # Personnages
        from core.characters import CharacterManager
        st.session_state.char_manager = CharacterManager(paths['char_dir'])

        # Paramètres UI
        st.session_state.current_model = config['model']['default']
        st.session_state.temperature = config['model']['temperature']
        st.session_state.top_p = config['model']['top_p']
        st.session_state.num_ctx = config['model'].get('num_ctx', 32768)
        st.session_state.k_retrieval = config['rag']['k_retrieval']
        st.session_state.show_sources = config['ui']['show_sources_default']
        st.session_state.show_debug_chunks = config['rag'].get('debug_show_context', False)
        st.session_state.mode = config['ui']['default_mode']

        # Nouveau : Sélection des sources pour le mode encyclopédique
        st.session_state.encyclo_source_filter = "rules_and_universe"

        # Compteur pour auto-save
        st.session_state.message_count = 0
        st.session_state.auto_save_interval = config['ui'].get('auto_save_interval', 5)

        # Historique des requêtes (navigation flèche haut/bas)
        st.session_state.query_history = []

        st.session_state.initialized = True


def check_corpus_changes(config):
    """Vérifie si le corpus a changé"""
    from core.rag import DocumentExtractor

    pdf_root = config['paths']['pdf_root']
    db_dir = config['paths']['db_dir']

    needs_reload, reason = DocumentExtractor.check_if_reload_needed(pdf_root, db_dir)

    return needs_reload, reason


@st.cache_resource(show_spinner=False)
def load_documents(_config):
    """Charge les documents (cached) avec progression"""
    extractor = DocumentExtractor()
    max_pages = _config['advanced'].get('max_pdf_pages')

    # Créer un placeholder principal unique
    main_container = st.empty()

    with main_container.container():
        st.markdown("### 📄 Lecture des documents")
        progress_bar = st.progress(0)
        status_text = st.empty()

    def progress_callback(current, total, message):
        """Callback pour afficher la progression"""
        if total > 0:
            progress = current / total
            with main_container.container():
                st.markdown("### 📄 Lecture des documents")
                progress_bar.progress(progress)
                status_text.info(f"📖 Fichier {current}/{total} : {message}")

    documents = extractor.extract_from_directory(
        _config['paths']['pdf_root'],
        max_pages,
        progress_callback=progress_callback
    )

    # Message de succès
    if documents:
        with main_container.container():
            st.markdown("### ✅ Documents chargés")
            st.success(f"🎉 {len(documents)} fichiers extraits avec succès")
        import time
        time.sleep(1.5)

    # Nettoyer complètement
    main_container.empty()

    return documents


@st.cache_resource(show_spinner=False)
def build_vectorstore(_config, _documents):
    """Construit le vectorstore (cached) avec progression détaillée"""
    from core.rag import VectorStore

    vector_store = VectorStore(_config)

    # Créer un placeholder principal unique
    main_container = st.empty()

    step = [0]  # Liste pour pouvoir modifier dans callback
    total_steps = 5

    def progress_callback(message):
        """Callback pour afficher le statut de création de la base"""
        step[0] += 1
        progress = step[0] / total_steps

        with main_container.container():
            st.markdown("### ⚙️ Création de la base vectorielle")
            st.progress(progress)
            st.info(f"🔧 {message}")

    result = vector_store.build_or_load(
        _documents,
        _config['paths']['db_dir'],
        _config['paths']['pdf_root'],
        progress_callback=progress_callback
    )

    # Message final
    if _documents:
        num_docs = len(_documents)
        with main_container.container():
            st.markdown("### ✅ Base vectorielle prête !")
            st.success(f"🎉 {num_docs} documents indexés et prêts à l'emploi")
        import time
        time.sleep(2)

    # Nettoyer complètement
    main_container.empty()

    return result


@st.cache_resource(show_spinner=False)
def load_vectorstore_only(_config):
    """Charge uniquement la base vectorielle existante (ultra rapide)"""
    from core.rag import VectorStore
    from langchain_chroma import Chroma

    vector_store = VectorStore(_config)

    # Placeholder unique
    main_container = st.empty()

    with main_container.container():
        st.markdown("### ⚡ Chargement rapide")
        st.info("Utilisation de la base vectorielle existante...")

    vectordb = Chroma(
        persist_directory=str(_config['paths']['db_dir']),
        embedding_function=vector_store.embeddings
    )

    # Vérifier que la base contient bien des vecteurs
    try:
        count = vectordb._collection.count()
        if count == 0:
            main_container.empty()
            return None  # Force un rebuild complet
    except Exception:
        pass

    # IMPORTANT: Créer les métadonnées si elles n'existent pas
    metadata_file = _config['paths']['db_dir'] / "corpus_metadata.json"
    if not metadata_file.exists():
        with main_container.container():
            st.markdown("### ⚙️ Mise à jour")
            st.info("Création des métadonnées de suivi...")
        DocumentExtractor.save_corpus_metadata(_config['paths']['pdf_root'], _config['paths']['db_dir'])

    with main_container.container():
        st.markdown("### ✅ Prêt")
        st.success("Base vectorielle chargée (aucun rechargement nécessaire)")

    import time
    time.sleep(1)
    main_container.empty()

    return vectordb


@st.cache_resource(show_spinner=False)
def _load_bm25_docs(_db_dir):
    """Charge les documents BM25 depuis le pickle (cached)"""
    import pickle
    bm25_file = Path(str(_db_dir)) / "bm25_docs.pkl"
    if not bm25_file.exists():
        return None
    try:
        with open(bm25_file, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def _get_bm25_retriever(_db_dir):
    """Construit et cache le BM25Retriever (construction une seule fois au démarrage)."""
    docs = _load_bm25_docs(_db_dir)
    if not docs:
        return None
    try:
        from langchain_community.retrievers.bm25 import BM25Retriever
        retriever = BM25Retriever.from_documents(docs)
        print(f"✅ BM25Retriever construit et mis en cache ({len(docs)} docs)")
        return retriever
    except Exception as e:
        print(f"⚠️ BM25 non disponible : {e}")
        return None


def get_qa_chain(config, vectordb, model, mode, temp, top_p, k, show_sources, system_prompt, memory, short_memory, level, source_filter="rules_and_universe", query=""):
    """Crée la chaîne QA (doit être recréée à chaque requête car contient la mémoire)"""
    from core.rag import RAGChain, BM25_AVAILABLE

    rag_chain = RAGChain(config)

    # Retriever vectoriel (avec filtre catégorie si mode encyclopédique)
    if mode == "Encyclopédique":
        if source_filter == "rules_only":
            filter_config = {"category": {"$in": ["rules", "unknown"]}}
        elif source_filter == "universe_only":
            filter_config = {"category": {"$in": ["universe_book", "novel"]}}
        else:  # rules_and_universe
            filter_config = {"category": {"$in": ["rules", "universe_book", "unknown"]}}

        vector_retriever = vectordb.as_retriever(
            search_kwargs={"k": k, "filter": filter_config}
        )
    else:
        vector_retriever = vectordb.as_retriever(search_kwargs={"k": k})

    # Hybrid search : combiner BM25 (mots-clés) + vectoriel (sémantique)
    # Le BM25Retriever est mis en cache — pas reconstruit à chaque requête
    retriever = vector_retriever
    if BM25_AVAILABLE:
        bm25_retriever = _get_bm25_retriever(config['paths']['db_dir'])
        if bm25_retriever:
            try:
                from core.rag import SimpleEnsembleRetriever
                bm25_retriever.k = k  # Ajuster k sans reconstruire l'index
                retriever = SimpleEnsembleRetriever(
                    retrievers=[bm25_retriever, vector_retriever],
                    weights=[0.4, 0.6]
                )
            except Exception as e:
                print(f"⚠️ Hybrid search désactivé ({e}), fallback vectoriel")

    # Retourner les sources si l'utilisateur veut voir les sources OU les chunks de debug
    return_sources = st.session_state.get('show_sources', False) or st.session_state.get('show_debug_chunks', False)

    qa_chain = rag_chain.create_qa_chain(
        retriever=retriever,
        model_name=model,
        mode="mj" if mode == "MJ immersif" else "encyclo",
        temperature=temp,
        top_p=top_p,
        return_sources=return_sources,
        system_prompt=system_prompt,
        memory=memory,
        short_memory=short_memory,
        level=level,
        query=query  # 🆕 Passer la query pour le re-ranking
    )

    return qa_chain, rag_chain


# Cache module-level du glossaire (chargé une seule fois)
_GLOSSARY_CACHE: dict = {}
_GLOSSARY_LOADED: bool = False


def _load_glossary() -> dict:
    """Charge prompts/glossary.json au premier appel, puis retourne le cache."""
    global _GLOSSARY_CACHE, _GLOSSARY_LOADED
    if not _GLOSSARY_LOADED:
        _GLOSSARY_LOADED = True
        glossary_path = Path("prompts/glossary.json")
        if glossary_path.exists():
            try:
                import json as _json
                data = _json.loads(glossary_path.read_text(encoding="utf-8"))
                _GLOSSARY_CACHE = data.get("mappings", {})
                print(f"📖 Glossaire chargé : {len(_GLOSSARY_CACHE)} termes ({glossary_path})")
            except Exception as _e:
                print(f"⚠️ Glossaire non chargeable : {_e}")
        else:
            print("ℹ️ Aucun glossaire trouvé (lance tools/build_glossary.py pour en créer un)")
    return _GLOSSARY_CACHE


def _expand_query_with_glossary(query: str) -> str:
    """Expansion instantanée via glossaire JSON (zéro latence LLM).

    Pour chaque terme officiel du glossaire, vérifie si un de ses synonymes
    apparaît dans la query. Si oui, ajoute le terme officiel à la query
    pour que BM25 et le vectoriel le trouvent.
    """
    glossary = _load_glossary()
    if not glossary:
        return query

    query_lower = query.lower()
    added: list = []

    for official_term, synonyms in glossary.items():
        # Ignorer si le terme officiel est déjà dans la query
        if official_term.lower() in query_lower:
            continue
        for synonym in (synonyms or []):
            if synonym.lower() in query_lower:
                added.append(official_term)
                break  # un synonyme suffit pour déclencher ce terme

    if added:
        expanded = f"{query} {' '.join(added)}"
        print(f"🔄 Query expansion (glossaire) : ajout de {added}")
        return expanded
    return query


def _expand_query_with_llm(query: str, model_name: str) -> str:
    """Expansion LLM en fallback quand le glossaire ne trouve rien.

    Appel rapide (num_predict=100) qui reformule la query avec la terminologie
    officielle du jeu, puis concatène avec l'originale pour couvrir les deux
    vocabulaires dans BM25.
    """
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOllama(model=model_name, temperature=0.0, num_predict=100)
        messages = [
            SystemMessage(content=(
                "Tu es expert du jeu de rôle 'Les Lames du Cardinal'. "
                "Reformule la question en utilisant les termes EXACTS du jeu. "
                "Exemples : 'combat' → 'affrontement Opposition Dramatique assaut', "
                "'magie' → 'Tarot des Ombres arcane sortilège', "
                "'points de vie' → 'Blessures Séquelles', "
                "'dégâts' → 'blessures conséquences'. "
                "Réponds UNIQUEMENT avec la question reformulée, sans explication."
            )),
            HumanMessage(content=query)
        ]
        result = llm.invoke(messages)
        rewritten = (result.content or "").strip()
        if rewritten and rewritten.lower() != query.lower():
            print(f"🔄 Query expansion (LLM fallback) : '{rewritten[:80]}'")
            return f"{query} {rewritten}"
    except Exception as _e:
        print(f"⚠️ LLM query expansion failed : {_e}")
    return query


def _expand_query(query: str, model_name: str) -> str:
    """Expande la query pour le retrieval RAG.

    Stratégie : glossaire d'abord (instantané), LLM en fallback si rien trouvé.
    Retourne toujours au moins la query originale.
    """
    # Étape 1 : glossaire JSON (zéro latence)
    expanded = _expand_query_with_glossary(query)
    if expanded != query:
        return expanded

    # Étape 2 : LLM fallback (~1-2s, uniquement si le glossaire n'a rien trouvé)
    return _expand_query_with_llm(query, model_name)


def process_query(query: str, config, mode: str, level: str, vectordb):
    """Traite une requête utilisateur"""
    try:
        # Prompt système
        system_prompt = load_prompt(config, 'mj_system' if mode == "MJ immersif" else 'encyclo_system')

        # Préparer la mémoire selon le mode
        if mode == "MJ immersif":
            memory = st.session_state.mj_memory
            memory_text = memory.format_for_prompt(n=config['memory']['short_memory_context'])
            short_memory_text = ""
            # Utiliser k_retrieval standard pour le mode MJ
            k_value = st.session_state.k_retrieval
            # Température normale pour le mode MJ
            temp_value = st.session_state.temperature
        else:
            memory = st.session_state.encyclo_memory
            memory_text = ""
            short_memory_text = memory.format_for_prompt(
                n=config['memory']['short_memory_context'],
                prefix_user="Question",
                prefix_assistant="Réponse"
            )
            # Utiliser la valeur du slider pour le mode encyclopédique
            k_value = st.session_state.get('encyclo_k_retrieval', config['rag'].get('k_retrieval_encyclo', 50))
            # Température à 0 pour éviter les hallucinations et forcer la fidélité au contexte
            temp_value = 0.0

        # ── Mode MJ immersif : chemin direct sans RAG ──────────────────────────
        if mode == "MJ immersif":
            from langchain_ollama import ChatOllama
            from langchain_core.messages import SystemMessage, HumanMessage

            model_name = st.session_state.current_model
            num_ctx = config['model'].get('num_ctx', 32768)
            num_predict = config['model'].get('num_predict', 2048)
            llm = ChatOllama(
                model=model_name,
                temperature=temp_value,
                top_p=st.session_state.top_p,
                num_ctx=num_ctx,
                num_predict=num_predict,
            )

            messages = [SystemMessage(content=system_prompt)]
            if memory_text.strip():
                messages.append(SystemMessage(content=f"Historique récent :\n{memory_text}"))
            messages.append(HumanMessage(content=query))

            import time as _time
            import re as _re
            _t0 = _time.time()
            result = llm.invoke(messages)
            _elapsed = _time.time() - _t0

            _meta = getattr(result, 'response_metadata', {}) or {}
            response_text = result.content if hasattr(result, 'content') else str(result)

            if '<think>' in response_text:
                after_think = _re.sub(r'<think>.*?</think>', '', response_text, flags=_re.DOTALL).strip()
                response_text = after_think if after_think else response_text

            result_obj = {
                "response": response_text,
                "sources": [],
                "confidence": 1.0,
                "elapsed": _elapsed,
                "tokens_in": _meta.get('prompt_eval_count', 0),
                "tokens_out": _meta.get('eval_count', 0),
                "cited_sources": [],
            }

            memory.add(query, response_text)

            from datetime import datetime
            from core.parser import ResponseParser
            parsed = ResponseParser.parse(response_text)
            st.session_state.game_state.update_from_parsed(parsed)
            st.session_state.timeline.append({
                "query": query,
                "response": response_text,
                "timestamp": datetime.now().isoformat(),
                "mode": mode,
            })
            if hasattr(st.session_state, 'statistics'):
                st.session_state.statistics.record_query(success=True)
            st.session_state.message_count += 1
            if st.session_state.message_count % st.session_state.auto_save_interval == 0:
                st.session_state.session_manager.save_session(
                    session_name="auto_save",
                    mj_memory=st.session_state.mj_memory,
                    encyclo_memory=st.session_state.encyclo_memory,
                    metadata={"auto_save": True}
                )
            return result_obj

        # ── Mode Encyclopédique : chemin RAG ───────────────────────────────────
        # Récupérer le filtre de source pour le mode encyclopédique
        source_filter = st.session_state.get('encyclo_source_filter', 'rules_and_universe')

        # Encyclopédique : two-phase retrieval (large fetch → re-rank CrossEncoder → k_final au LLM)
        # MJ immersif : retrieval direct avec k_value
        if mode == "Encyclopédique":
            k_fetch = config['rag'].get('k_initial_retrieval', 40)
        else:
            k_fetch = k_value

        qa_chain, rag_chain = get_qa_chain(
            config=config,
            vectordb=vectordb,
            model=st.session_state.current_model,
            mode=mode,
            temp=temp_value,
            top_p=st.session_state.top_p,
            k=k_fetch,
            show_sources=st.session_state.show_sources,
            system_prompt=system_prompt,
            memory=memory_text,
            short_memory=short_memory_text,
            level=level,
            source_filter=source_filter,
            query=query
        )

        # Récupérer les documents avec scores de pertinence réels
        retriever = qa_chain["retriever"]
        format_context = qa_chain["format_context"]

        # En mode encyclopédique : format context avec marqueurs de référence
        # Limite à 1200 chars par chunk pour éviter de saturer le contexte LLM
        _CHUNK_MAX_CHARS = 3000
        if mode == "Encyclopédique":
            # Extraire les mots-clés significatifs de la query pour détecter les correspondances
            import re as _re2
            _query_words = set(w.lower() for w in _re2.findall(r'\w{4,}', query))

            def format_context(docs):
                import re as _re_fc
                direct_hits = []
                parts = []
                for i, doc in enumerate(docs, 1):
                    page = doc.metadata.get('page', '?')
                    source = doc.metadata.get('source', '?')
                    section = doc.metadata.get('section', '')
                    content = doc.page_content
                    if len(content) > _CHUNK_MAX_CHARS:
                        content = content[:_CHUNK_MAX_CHARS] + "…"

                    # Détecte si ce chunk contient directement le sujet demandé
                    _content_words = set(w.lower() for w in _re_fc.findall(r'\w{4,}', content))
                    _overlap = len(_query_words & _content_words)
                    # Cherche si un mot-clé apparaît dans une ligne de titre (## ...)
                    _title_line = next((ln for ln in content.split('\n') if ln.strip().startswith('#')), '')
                    _has_title = bool(_title_line) and any(w in _title_line.lower() for w in _query_words)
                    _is_direct = _has_title or _overlap >= max(2, len(_query_words) * 0.4)

                    if _is_direct:
                        # Si le chunk contient plusieurs arcanes (## N ...), extraire seulement la section pertinente
                        _all_headings = list(_re_fc.finditer(r'## \d+\s+\w', content))
                        if len(_all_headings) > 1:
                            for _mh in _all_headings:
                                _h_text = content[_mh.start():_mh.start()+120].lower()
                                if any(w in _h_text for w in _query_words):
                                    _sec_start = _mh.start()
                                    _next_h = _re_fc.search(r'## \d+\s+\w', content[_sec_start + 1:])
                                    _sec_end = _sec_start + 1 + _next_h.start() if _next_h else len(content)
                                    content = content[_sec_start:_sec_end].rstrip()
                                    print(f"  📌 Chunk {i} (p.{page}) multi-arcane : section extraite")
                                    break
                        direct_hits.append((i, source, page, content))
                    elif direct_hits:
                        # Si on a déjà un hit direct, tronquer ce chunk quand il démarre
                        # un nouvel arcane (## N …) dont les mots-clés ne matchent pas la requête.
                        # Pas de \n requis avant ## : le chunk p.245 a ". ## 1 La Tisserande" sans \n
                        _new_arcane = _re_fc.search(r'## \d+\s+\w', content)
                        if _new_arcane:
                            _ha_start = _new_arcane.start()
                            heading_text = content[_ha_start:_ha_start + 120].lower()
                            if not any(w in heading_text for w in _query_words):
                                content = content[:_ha_start].rstrip()
                                print(f"  ✂️ Chunk {i} tronqué à l'arcane suivant (p.{page})")

                    ref_header = f"[Réf. {i} — {source}, p.{page}]"
                    if section:
                        ref_header += f" — {section}"
                    parts.append(f"{ref_header}\n{content}")

                result = ""
                if direct_hits:
                    result += ">>> RÉPONSE DIRECTE — CONTENU À UTILISER EN PRIORITÉ <<<\n"
                    result += "=" * 60 + "\n"
                    for i, source, page, content in direct_hits:
                        result += f"[Réf. {i} — {source}, p.{page}]\n{content}\n"
                    result += "=" * 60 + "\n\n"

                result += "\n\n---\n\n".join(parts)
                return result

        # ── Query expansion : adapte le vocabulaire utilisateur aux termes du jeu ──
        # Ex: "système de combat" → "système de combat Oppositions dramatiques affrontements..."
        # Automatique, sans maintenance manuelle. Utilisé uniquement pour le retrieval.
        _qe_enabled = config.get('rag', {}).get('enable_query_expansion', True)
        if mode == "Encyclopédique" and _qe_enabled:
            _retrieval_query = _expand_query(query, st.session_state.current_model)
        else:
            _retrieval_query = query

        # Score de pertinence réel via Chroma (0=hors-sujet, 1=parfait)
        confidence = 0.0
        try:
            scored_docs = vectordb.similarity_search_with_relevance_scores(_retrieval_query, k=5)
            if scored_docs:
                confidence = sum(s for _, s in scored_docs) / len(scored_docs)
                print(f"📊 Scores de pertinence : {[round(s,2) for _,s in scored_docs[:3]]}")
        except Exception:
            pass

        # Récupérer les chunks (k_fetch docs) — avec requête étendue
        source_docs = retriever.invoke(_retrieval_query)

        # Filtrer par catégorie APRÈS retrieval (le BM25 n'a pas de filtre natif)
        if mode == "Encyclopédique":
            _sf = st.session_state.get('encyclo_source_filter', 'rules_and_universe')
            if _sf == "rules_only":
                _allowed = {"rules", "unknown"}
            elif _sf == "universe_only":
                _allowed = {"universe_book", "novel"}
            else:
                _allowed = {"rules", "universe_book", "unknown"}
            source_docs = [d for d in source_docs if d.metadata.get('category', 'unknown') in _allowed]

        # DIAGNOSTIC : afficher tous les chunks initiaux
        if mode == "Encyclopédique":
            print(f"\n📋 DIAGNOSTIC — {len(source_docs)} chunks (filtre={_sf}) :")
            for _di, _dd in enumerate(source_docs, 1):
                _dp = _dd.metadata.get('page', '?')
                _ds = _dd.metadata.get('source', '?')
                _dcat = _dd.metadata.get('category', '?')
                _dc = _dd.page_content[:80].replace('\n', ' ')
                print(f"  [{_di:02d}] p.{_dp} [{_dcat}] ({_ds}): {_dc}...")

        # Phase 2 : re-ranker → réduire à k_value pour le LLM
        if mode == "Encyclopédique" and len(source_docs) > k_value:
            if rag_chain and rag_chain.reranker:
                source_docs = rag_chain.rerank_documents(query, source_docs, k_value)
                print(f"🎯 Two-phase : {k_fetch} → {len(source_docs)} chunks après re-ranking")
            else:
                source_docs = source_docs[:k_value]
                print(f"📋 Two-phase : {k_fetch} → {len(source_docs)} chunks (tronqué, pas de re-ranker)")

        # Avertissement console si pertinence faible
        if confidence < 0.3:
            print(f"⚠️ Pertinence faible ({confidence:.0%}) — contexte probablement hors-sujet")

        context_text = format_context(source_docs)

        # En mode encyclopédique : injecter le premier hit direct dans la question
        # Les LLMs suivent mieux le contenu de la question que les instructions de contexte
        _query_to_use = query
        if mode == "Encyclopédique":
            import re as _re_aug
            _qw_aug = set(w.lower() for w in _re_aug.findall(r'\w{4,}', query))
            for _aug_i, _aug_doc in enumerate(source_docs, 1):
                _aug_cw = set(w.lower() for w in _re_aug.findall(r'\w{4,}', _aug_doc.page_content))
                _aug_tl = next((ln for ln in _aug_doc.page_content.split('\n') if ln.strip().startswith('#')), '')
                _aug_ht = bool(_aug_tl) and any(w in _aug_tl.lower() for w in _qw_aug)
                _aug_ov = len(_qw_aug & _aug_cw)
                if _aug_ht or _aug_ov >= max(2, len(_qw_aug) * 0.4):
                    _aug_pg = _aug_doc.metadata.get('page', '?')
                    _query_to_use = (
                        f"Voici la définition officielle trouvée dans les documents "
                        f"(Réf. {_aug_i}, p.{_aug_pg}) :\n"
                        f"---\n"
                        f"{_aug_doc.page_content}\n"
                        f"---\n\n"
                        f"{query}"
                    )
                    print(f"🎯 Query augmentée avec Réf. {_aug_i}, p.{_aug_pg}")
                    break

        import time as _time
        import re as _re
        _t0 = _time.time()
        result = qa_chain["chain"].invoke({"context": context_text, "question": _query_to_use})
        _elapsed = _time.time() - _t0

        _meta = getattr(result, 'response_metadata', {}) or {}
        _tokens_in = _meta.get('prompt_eval_count', 0)
        _tokens_out = _meta.get('eval_count', 0)

        # 1. Récupérer le contenu brut
        if hasattr(result, 'content'):
            response_text = result.content or ""
        else:
            response_text = str(result)

        # 2. Si vide, chercher dans additional_kwargs (certaines versions de langchain-ollama
        #    placent le contenu des modèles "thinking" dans ce champ plutôt que dans content)
        if not response_text.strip() and hasattr(result, 'additional_kwargs'):
            ak = result.additional_kwargs
            response_text = (
                ak.get('thinking') or ak.get('reasoning_content') or ak.get('think') or ""
            ).strip()
            if response_text:
                print(f"💡 Contenu récupéré depuis additional_kwargs")

        # 3. Supprimer les blocs <think>...</think> et garder la réponse visible
        if '<think>' in response_text:
            after_think = _re.sub(r'<think>.*?</think>', '', response_text, flags=_re.DOTALL).strip()
            if after_think:
                response_text = after_think
            else:
                # Seul le thinking a été généré — l'utiliser comme réponse
                m = _re.search(r'<think>(.*?)</think>', response_text, _re.DOTALL)
                response_text = m.group(1).strip() if m else response_text

        # Extraire les références citées (Réf.X) depuis la réponse encyclopédique
        cited_sources = []
        if mode == "Encyclopédique":
            seen_refs = set()
            # Matche (Réf.1), (Réf. 1), (Réf. 1 — ...) et [Réf. 1 — ...]
            for m in _re.finditer(r'[\(\[]\s*Réf\.\s*(\d+)', response_text):
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(source_docs) and idx not in seen_refs:
                    seen_refs.add(idx)
                    doc = source_docs[idx]
                    cited_sources.append({
                        "ref": idx + 1,
                        "page": doc.metadata.get('page', '?'),
                        "source": doc.metadata.get('source', '?'),
                        "path": doc.metadata.get('path', ''),
                        "section": doc.metadata.get('section', ''),
                    })
            # Si la query a été augmentée (hit direct injecté dans la question),
            # le modèle n'a pas pu citer (Réf.X) → ajouter automatiquement le hit direct
            if not cited_sources and _query_to_use != query and source_docs:
                doc = source_docs[0]
                cited_sources.append({
                    "ref": 1,
                    "page": doc.metadata.get('page', '?'),
                    "source": doc.metadata.get('source', '?'),
                    "path": doc.metadata.get('path', ''),
                    "section": doc.metadata.get('section', ''),
                })

        # Debug
        print(f"📝 Réponse : {len(response_text)} chars | Confiance : {confidence:.0%} | Sources : {len(source_docs)}")
        if not response_text.strip():
            print(f"⚠️ Réponse vide ! type={type(result).__name__} | content={repr(getattr(result,'content','?'))[:200]} | ak_keys={list(getattr(result,'additional_kwargs',{}).keys())}")
        if source_docs:
            for i, doc in enumerate(source_docs[:3], 1):
                print(f"  Chunk {i}: [{doc.metadata.get('category','?')}] {doc.metadata.get('source','?')} — {doc.page_content[:80]}...")

        # Créer l'objet résultat
        result_obj = {
            "response": response_text,
            "sources": source_docs,
            "confidence": confidence,
            "elapsed": _elapsed,
            "tokens_in": _tokens_in,
            "tokens_out": _tokens_out,
            "cited_sources": cited_sources,
        }

        # Enregistrer dans la mémoire
        memory.add(query, result_obj['response'])

        # Parser la réponse + alimenter la timeline
        from datetime import datetime
        if mode == "MJ immersif":
            from core.parser import ResponseParser
            parsed = ResponseParser.parse(result_obj['response'])
            st.session_state.game_state.update_from_parsed(parsed)
        st.session_state.timeline.append({
            "query": query,
            "response": result_obj['response'],
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
        })

        # Statistiques
        if hasattr(st.session_state, 'statistics'):
            st.session_state.statistics.record_query(success=True)

        # Auto-save
        st.session_state.message_count += 1
        if st.session_state.message_count % st.session_state.auto_save_interval == 0:
            st.session_state.session_manager.save_session(
                session_name="auto_save",
                mj_memory=st.session_state.mj_memory,
                encyclo_memory=st.session_state.encyclo_memory,
                metadata={"auto_save": True}
            )

        return result_obj

    except Exception as e:
        if hasattr(st.session_state, 'statistics'):
            st.session_state.statistics.record_query(success=False)

        err_str = str(e)
        # Crash VRAM / llama-server killed
        if "CUDA error" in err_str or "llama-server process has terminated" in err_str or "ResponseError" in type(e).__name__:
            model = st.session_state.get('current_model', '?')
            raise RuntimeError(
                f"💥 **Mémoire GPU insuffisante** — le modèle `{model}` a manqué de VRAM "
                f"pour cette génération.\n\n"
                f"**Solutions :**\n"
                f"- Utilise `mistral-nemo` ou `gemma4-12b` (7 GB) pour les scènes créatives\n"
                f"- Réserve `qwen3.6:35b-a3b` pour des questions courtes et précises\n"
                f"- Réduis le contexte dans `config.yaml` : `num_ctx: 8192`"
            ) from e
        raise e


# Instructions de longueur/format selon le niveau choisi
_LEVEL_INSTRUCTIONS = {
    # Mode MJ immersif
    "Résumé court": (
        "LONGUEUR : 2 à 3 paragraphes courts et percutants. Va à l'essentiel."
    ),
    "Scène détaillée": (
        "LONGUEUR : 4 à 6 paragraphes. Inclus des détails sensoriels "
        "(sons, odeurs, lumières, textures) pour ancrer la scène."
    ),
    "Longue narration immersive": (
        "LONGUEUR : 8 à 12 paragraphes minimum. Développe chaque élément en profondeur : "
        "décors fouillés, atmosphère, dialogues, tensions dramatiques, arrière-pensées des "
        "personnages. Prends le temps de planter le décor, d'installer la tension, et de "
        "donner vie à chaque détail. Ne résume pas — décris, montre, fais ressentir."
    ),
    # Mode encyclopédique
    "Points clés": (
        "FORMAT : Réponds en 3 à 5 points clés maximum, format bullet points (•). "
        "Sois direct et factuel. Pas de phrases introductives."
    ),
    "Explication complète": (
        "FORMAT : Explique la règle ou le concept en détail avec les mécaniques précises, "
        "au moins un exemple de jeu concret, et les exceptions notables."
    ),
    "Détail exhaustif": (
        "FORMAT : Réponse exhaustive avec titres markdown (## et ###) : définition, "
        "mécaniques détaillées, cas particuliers, interactions avec d'autres règles, "
        "plusieurs exemples de jeu. Couvre tous les aspects du sujet."
    ),
}


def process_creative_query(query: str, config, level: str):
    """Mode narratif pur : appel direct au LLM sans RAG.
    Utilise uniquement le system_prompt du jeu comme contexte — pas de chunks de documents.
    """
    import re as _re

    try:
        system_prompt = load_prompt(config, 'mj_system')
        model = st.session_state.current_model
        temp = st.session_state.temperature
        top_p = st.session_state.top_p

        level_instruction = _LEVEL_INSTRUCTIONS.get(level, _LEVEL_INSTRUCTIONS["Scène détaillée"])

        # Contexte de la mémoire courante
        memory_text = st.session_state.mj_memory.format_for_prompt(
            n=config['memory']['short_memory_context']
        )

        from langchain_ollama import ChatOllama
        from langchain_core.prompts import PromptTemplate

        # Créer le LLM directement — sans RAGChain pour éviter
        # le chargement du re-ranker et toute opération RAG
        num_ctx = st.session_state.get('num_ctx', config.get('model', {}).get('num_ctx', 32768))
        num_predict = config.get('model', {}).get('num_predict', 2048)
        _thinking = ('qwen3', 'gemma4', 'gemma3', 'deepseek-r1', 'qwq')
        _extra = {'think': False} if any(f in model.lower() for f in _thinking) else {}
        try:
            llm = ChatOllama(model=model, temperature=temp, top_p=top_p,
                             num_ctx=num_ctx, num_predict=num_predict, **_extra)
        except TypeError:
            try:
                llm = ChatOllama(model=model, temperature=temp, top_p=top_p,
                                 num_ctx=num_ctx, num_predict=num_predict)
            except TypeError:
                llm = ChatOllama(model=model, temperature=temp)

        template = f"""{system_prompt}

Mémoire de la partie :
{memory_text}

{level_instruction}

Demande du joueur : {{question}}

Réponds librement en te basant sur ta connaissance de "Les Lames du Cardinal" et de la France du XVIIème siècle sous Louis XIII. Sois immersif, précis et cohérent avec l'univers. Ne mentionne jamais de "documents" ni de "contexte".

Réponds en suivant ce format :
1. Description immersive (respecte impérativement les consignes de longueur ci-dessus)
2. Propose 2 à 4 options claires (format: OPTION 1: ..., OPTION 2: ..., etc.)
3. Si nécessaire, liste les conséquences structurées:
   - [PNJ:Nom:Statut]
   - [Lieu:Nom:Statut]
   - [Intrigue:Nom:Statut]

Ta réponse :"""

        prompt = PromptTemplate(template=template, input_variables=["question"])
        # Ne pas utiliser StrOutputParser — extraire manuellement pour gérer
        # les modèles thinking (gemma4, qwen3) qui retournent .content vide
        chain = prompt | llm

        import time as _time
        _t0 = _time.time()
        result = chain.invoke({"question": query})
        _elapsed = _time.time() - _t0

        _meta = getattr(result, 'response_metadata', {}) or {}
        _tokens_in = _meta.get('prompt_eval_count', 0)
        _tokens_out = _meta.get('eval_count', 0)

        # Extraction robuste (même logique que process_query)
        if hasattr(result, 'content'):
            response_text = result.content or ""
        else:
            response_text = str(result)

        if not response_text.strip() and hasattr(result, 'additional_kwargs'):
            ak = result.additional_kwargs
            response_text = (
                ak.get('thinking') or ak.get('reasoning_content') or ak.get('think') or ""
            ).strip()

        # Strip balises thinking
        if '<think>' in response_text:
            after = _re.sub(r'<think>.*?</think>', '', response_text, flags=_re.DOTALL).strip()
            response_text = after if after else response_text

        if not response_text.strip():
            print(f"⚠️ Réponse vide (créatif) ! type={type(result).__name__} | "
                  f"content={repr(getattr(result,'content','?'))[:200]} | "
                  f"ak_keys={list(getattr(result,'additional_kwargs',{}).keys())}")

        print(f"✨ Mode narratif pur : {len(response_text)} chars générés")

        # Enregistrer dans la mémoire MJ
        st.session_state.mj_memory.add(query, response_text)

        # Parser pour mettre à jour le game_state
        from core.parser import ResponseParser
        parsed = ResponseParser.parse(response_text)
        st.session_state.game_state.update_from_parsed(parsed)

        from datetime import datetime
        st.session_state.timeline.append({
            "query": query,
            "response": response_text,
            "timestamp": datetime.now().isoformat(),
            "mode": "Narratif pur",
        })

        return {
            "response": response_text,
            "sources": [],
            "confidence": None,
            "elapsed": _elapsed,
            "tokens_in": _tokens_in,
            "tokens_out": _tokens_out,
        }

    except Exception as e:
        raise e


@st.cache_data(show_spinner=False)
def _render_pdf_page(pdf_path: str, page_num: int) -> bytes:
    """Rend une page PDF en image PNG via PyMuPDF (résolution x2)."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            return None
        page = doc[page_num - 1]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        png = pix.tobytes("png")
        doc.close()
        return png
    except Exception as e:
        print(f"⚠️ Erreur rendu page PDF: {e}")
        return None


def _find_pdf_path(filename: str, config: dict) -> str:
    """Cherche le chemin absolu d'un PDF dans le dossier Data."""
    import os
    pdf_root = config['paths'].get('pdf_root', 'Data')
    base_dir = config['paths'].get('base_dir', '.')
    for root, _dirs, files in os.walk(os.path.join(base_dir, pdf_root)):
        if filename in files:
            return os.path.join(root, filename)
    return None


def main():
    """Fonction principale"""
    # Initialisation
    config = init_app()
    init_session_state(config)

    # CSS personnalisé
    from core.utils import ColorScheme
    st.markdown(ColorScheme.get_css(), unsafe_allow_html=True)

    # Titre tout en haut pour maximiser l'espace
    st.title("🗡️ Les Lames du Cardinal")

    # Sidebar avec les fiches de personnages
    from app_ui import render_sidebar
    render_sidebar()

    # ── Presets de mode : détection AVANT le rendu des colonnes ──────────────
    # Le sélecteur de mode est dans col_config, mais le toggle creative_mode est
    # dans col_main (rendu en premier). On doit appliquer les presets ici pour
    # pouvoir modifier creative_mode avant que son widget soit instancié.
    from app_ui import _apply_mode_presets, _EXCLUDED
    from core.utils import get_ollama_models
    _avail_models = [m for m in get_ollama_models() if m not in _EXCLUDED]
    _incoming_mode = st.session_state.get("mode_selector",
                                          st.session_state.get("mode", "MJ immersif"))
    # Synchroniser st.session_state.mode immédiatement — le selectbox de mode
    # est dans col_config (rendu APRÈS col_main), donc sans cette ligne,
    # col_main lirait l'ancienne valeur du mode.
    st.session_state.mode = _incoming_mode
    if _incoming_mode != st.session_state.get("_last_applied_mode"):
        _apply_mode_presets(_incoming_mode, _avail_models)
        st.session_state._last_applied_mode = _incoming_mode
    # ─────────────────────────────────────────────────────────────────────────

    # Layout principal - colonne large pour le contenu principal, colonne droite pour la config
    col_main, col_config = st.columns([4, 1])

    # Colonne principale
    with col_main:
        # Timeline (tous les modes)
        if config['ui'].get('timeline_enabled', True):
            from app_ui import render_timeline
            render_timeline()

        # Initialiser le flag de première requête
        if 'first_query_sent' not in st.session_state:
            st.session_state.first_query_sent = False

        # Chargement des documents et vectorstore - LOGIQUE INTELLIGENTE
        # Masquer après la première requête pour gagner de l'espace
        if not st.session_state.first_query_sent:
            st.markdown("---")

            # Titre de section visible
            col_load1, col_load2 = st.columns([1, 4])
            with col_load1:
                st.markdown("## 📚")
            with col_load2:
                st.markdown("## Chargement du corpus")

            st.markdown("---")

        # Vérifier si un rechargement est nécessaire
        needs_reload, reason = check_corpus_changes(config)

        if needs_reload:
            if not st.session_state.first_query_sent:
                # Afficher pourquoi on recharge
                st.warning(f"🔄 **Rechargement nécessaire** : {reason}")

            # Chargement complet avec progression
            documents = load_documents(config)

            if not documents:
                st.error("❌ **Aucun document trouvé !**")
                st.warning(f"Vérifie que des PDFs sont présents dans : `{config['paths']['pdf_root']}`")
                st.info("💡 Dépose tes PDFs de règles dans ce dossier et relance l'application.")
                st.stop()

            # Construction de la base vectorielle
            vectordb = build_vectorstore(config, documents)
        else:
            # Chargement rapide (base existe et corpus inchangé)
            if not st.session_state.first_query_sent:
                st.success(f"✅ **{reason}** - Chargement rapide activé !")

            # Charger uniquement la base vectorielle (ultra rapide)
            vectordb = load_vectorstore_only(config)

            # Si la base est vide (0 vecteurs), forcer un rebuild complet
            if vectordb is None:
                st.warning("⚠️ Base vectorielle vide détectée — reconstruction en cours...")
                load_vectorstore_only.clear()
                documents = load_documents(config)
                if not documents:
                    st.error("❌ **Aucun document trouvé !**")
                    st.stop()
                vectordb = build_vectorstore(config, documents)

            # Lire les métadonnées pour afficher les stats
            if not st.session_state.first_query_sent:
                metadata_file = config['paths']['db_dir'] / "corpus_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            import json
                            metadata = json.load(f)
                            num_docs = metadata.get('total_files', 0)
                            st.info(f"📊 Base vectorielle contient {num_docs} documents")
                    except Exception:
                        pass

        # Afficher stats finales (uniquement si on a rechargé ET si c'est avant la première requête)
        if not st.session_state.first_query_sent and needs_reload and 'documents' in locals():
            st.markdown("---")
            st.markdown("### 📊 Statistiques du corpus")
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("📄 Documents", len(documents), delta="Prêt", delta_color="normal")
            with col_stat2:
                total_chars = sum(len(content) for content in documents.values())
                st.metric("📝 Caractères", f"{total_chars:,}")
            with col_stat3:
                # Estimer le nombre de chunks
                estimated_chunks = total_chars // config['rag']['chunk_size']
                st.metric("🧩 Chunks estimés", f"~{estimated_chunks:,}")

        # Petite note discrète après la première requête
        if st.session_state.first_query_sent:
            # Lire le nombre de docs pour affichage compact
            metadata_file = config['paths']['db_dir'] / "corpus_metadata.json"
            num_docs = 0
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        import json
                        metadata = json.load(f)
                        num_docs = metadata.get('total_files', 0)
                except Exception:
                    pass
            st.caption(f"📚 Base vectorielle chargée ({num_docs} documents)")

        st.markdown("---")

        # Zone d'interaction
        st.markdown("### 💬 Interaction")

        # Niveau de narration / détail selon le mode
        if st.session_state.mode == "MJ immersif":
            level = st.selectbox(
                "Niveau de narration:",
                ["Résumé court", "Scène détaillée", "Longue narration immersive"],
                key="narration_level",
                help="Contrôle la longueur et la richesse de la réponse du MJ"
            )
        else:
            level = st.selectbox(
                "Niveau de détail:",
                ["Points clés", "Explication complète", "Détail exhaustif"],
                key="narration_level",
                help="Points clés = bullet points concis | Explication complète = règles + exemples | Détail exhaustif = tout, y compris cas particuliers"
            )

        # Historique des requêtes — clic = renvoi immédiat (sans passer par le form)
        if st.session_state.query_history:
            with st.expander(f"🕐 Historique ({len(st.session_state.query_history)} requêtes)", expanded=False):
                for _i, _past_q in enumerate(st.session_state.query_history):
                    if st.button(
                        f"↩ {_past_q[:80]}{'…' if len(_past_q) > 80 else ''}",
                        key=f"hist_btn_{_i}",
                        use_container_width=True
                    ):
                        st.session_state["_prefill_query"] = _past_q
                        st.rerun()

        # Pré-remplir le champ si une question historique a été sélectionnée
        if "_prefill_query" in st.session_state:
            st.session_state["user_input"] = st.session_state.pop("_prefill_query")

        # Formulaire pour les nouvelles requêtes
        with st.form(key="query_form", clear_on_submit=True):
            user_query = st.text_input(
                "Ta question ou action (Entrée pour envoyer):",
                placeholder="Ex: Explique-moi le Voleur sans Mémoire",
                key="user_input"
            )

            # Avertissement pour questions trop larges
            if user_query and any(word in user_query.lower() for word in ["liste", "tous", "toutes", "22", "vingt"]):
                st.warning("⚠️ **Attention** : Les questions demandant des listes complètes peuvent générer des hallucinations. Le RAG fonctionne mieux avec des questions ciblées (ex: 'Explique l'arcane X').")

            submit = st.form_submit_button("📤 Envoyer", type="primary", use_container_width=True)

        active_query = user_query.strip() if submit and user_query else None

        if active_query:
            # Sauvegarder dans l'historique (10 entrées max, sans doublons consécutifs)
            history = st.session_state.query_history
            if not history or history[0] != active_query:
                history.insert(0, active_query)
                st.session_state.query_history = history[:10]

            with st.spinner("✨ Le MJ crée..." if st.session_state.mode == "MJ immersif" else "🤔 Recherche en cours..."):
                try:
                    result = process_query(
                        query=active_query,
                        config=config,
                        mode=st.session_state.mode,
                        level=level,
                        vectordb=vectordb
                    )

                    st.session_state.first_query_sent = True
                    st.session_state._last_result = result
                    st.session_state._last_query = active_query

                except RuntimeError as e:
                    st.error(str(e))
                except Exception as e:
                    err_str = str(e)
                    if "CUDA error" in err_str or "llama-server process has terminated" in err_str:
                        model = st.session_state.get('current_model', '?')
                        st.error(f"💥 **Crash VRAM** — `{model}` est trop grand pour cette génération.")
                        st.info("Utilise `mistral-nemo` ou `gemma4-12b` pour les scènes créatives longues.")
                    else:
                        st.error(f"❌ Erreur: {e}")
                        import traceback
                        st.exception(traceback.format_exc())

        # ─── Affichage du dernier résultat ────────────────────────────────────
        # Séparé du traitement pour survivre aux reruns (boutons PDF, etc.)
        if st.session_state.get('_last_result'):
            _r = st.session_state._last_result
            _q = st.session_state._last_query

            st.markdown("### 💬 Question")
            st.info(f"**{_q}**")
            st.markdown("### ✅ Réponse")

            if _r.get('confidence') is not None and _r['confidence'] < 0.3:
                st.warning(
                    f"⚠️ **Pertinence faible ({_r['confidence']:.0%})** — "
                    "Les documents récupérés sont peut-être hors-sujet. "
                    "Pour les questions de règles, utilise le mode **Encyclopédique** "
                    "avec le filtre **Règles uniquement**."
                )

            if _r['response'] and len(_r['response'].strip()) > 0:
                # Détection de boucle de répétition :
                # - même phrase longue (>60 chars) répétée 4+ fois
                # - OU patron suspect répété 3+ fois
                # Seuil élevé pour éviter les faux positifs sur les réponses structurées
                from collections import Counter as _Counter
                _lines = [l.strip() for l in _r['response'].split('\n') if len(l.strip()) > 60]
                _line_counts = _Counter(_lines)
                _suspicious = ["une créature ou un lieu en danger", "selon le contexte fourni", "Il est également mentionné que"]
                hallucination_detected = (
                    any(c >= 4 for c in _line_counts.values()) or
                    any(_r['response'].count(p) >= 3 for p in _suspicious)
                )

                if hallucination_detected:
                    st.error("⚠️ ALERTE : Boucle de répétition détectée — réponse tronquée ci-dessous")
                    st.warning("Le modèle a tourné en boucle. Essaie une question plus ciblée ou un autre modèle.")
                    with st.expander("⚠️ Réponse (répétitions présentes)"):
                        st.markdown(_r['response'])
                else:
                    st.markdown(_r['response'])
            else:
                st.error("❌ Le modèle n'a pas généré de réponse.")
                if st.session_state.get('show_sources', True) and _r.get('sources'):
                    with st.expander("🔍 Sources récupérées (pour diagnostic)"):
                        for i, doc in enumerate(_r['sources'][:5], 1):
                            st.markdown(f"**Chunk {i}** (source: {doc.metadata.get('source', 'inconnu')})")
                            st.text(doc.page_content[:400].replace("\n", " ") + "...")
                            st.markdown("---")

            # Métriques (confiance + temps + tokens)
            _caption_parts = []
            if _r.get('confidence') is not None and _r['confidence'] > 0:
                _cc = "🟢" if _r['confidence'] > 0.7 else "🟡" if _r['confidence'] > 0.4 else "🔴"
                _caption_parts.append(f"{_cc} Confiance RAG: {_r['confidence']:.0%}")
            if _r.get('elapsed'):
                _caption_parts.append(f"⏱️ {_r['elapsed']:.1f}s")
            if _r.get('tokens_in'):
                _caption_parts.append(f"📥 {_r['tokens_in']} tk")
            if _r.get('tokens_out'):
                _caption_parts.append(f"📤 {_r['tokens_out']} tk")
            if _caption_parts:
                st.caption(" · ".join(_caption_parts))

            # Boutons sources citées (encyclopédique)
            if st.session_state.mode == "Encyclopédique" and _r.get('cited_sources'):
                st.markdown("**📚 Sources :**")
                _btn_cols = st.columns(min(len(_r['cited_sources']), 5))
                for _i, _ref in enumerate(_r['cited_sources']):
                    _col = _btn_cols[_i % len(_btn_cols)]
                    _page_lbl = f"p.{_ref['page']}" if _ref['page'] != '?' else _ref['source']
                    with _col:
                        if st.button(f"📄 {_page_lbl}", key=f"pdfref_{_ref['source']}_{_ref['page']}_{_i}"):
                            st.session_state._pdf_view = _ref
                            st.session_state._pdf_view_config = config

            # Debug chunks
            if st.session_state.get('show_debug_chunks', False) and _r.get('sources'):
                filter_names = {
                    "rules_only": "📖 Règles uniquement",
                    "universe_only": "🌍 Univers + Romans",
                    "rules_and_universe": "📖🌍 Règles + Univers (sans romans)"
                }
                _sf = st.session_state.get('encyclo_source_filter', 'rules_and_universe')
                with st.expander(f"🔍 DEBUG: Chunks récupérés ({len(_r['sources'])} chunks)"):
                    st.info(f"🎯 Filtre actif : **{filter_names.get(_sf, _sf)}**")
                    for i, doc in enumerate(_r['sources'], 1):
                        st.markdown(f"### Chunk {i}/{len(_r['sources'])}")
                        if hasattr(doc, 'metadata') and doc.metadata:
                            st.caption(f"Source: {doc.metadata.get('source', '?')} | p.{doc.metadata.get('page', '?')} | {doc.metadata.get('category', '?')}")
                        st.text_area(f"Contenu chunk {i}", doc.page_content, height=200, key=f"debug_chunk_{i}")
                        st.markdown("---")

            # Sources normales
            if st.session_state.show_sources and _r.get('sources'):
                with st.expander(f"📚 Sources ({len(_r['sources'])} documents)"):
                    for i, doc in enumerate(_r['sources'], 1):
                        _page = doc.metadata.get('page', '?')
                        _src = doc.metadata.get('source', 'inconnu')
                        st.markdown(f"**Source {i}** — {_src}, p.{_page}")
                        st.text(doc.page_content[:400].replace("\n", " ") + "...")

        # Visionneuse PDF (persiste entre requêtes, s'affiche quand une source est cliquée)
        if '_pdf_view' in st.session_state and st.session_state._pdf_view:
            _view = st.session_state._pdf_view
            _cfg = st.session_state.get('_pdf_view_config', config)
            _view_title = f"📄 {_view['source']} — p.{_view['page']}"
            if _view.get('section'):
                _view_title += f"  ({_view['section']})"
            with st.expander(_view_title, expanded=True):
                _pdf_path = _find_pdf_path(_view['source'], _cfg)
                if _pdf_path and _view['page'] != '?':
                    _png = _render_pdf_page(_pdf_path, int(_view['page']))
                    if _png:
                        st.image(_png, use_container_width=True)
                    else:
                        st.warning("Impossible de rendre cette page.")
                else:
                    st.info(f"Source : {_view['source']}, p.{_view['page']}")
                if st.button("✖ Fermer la visionneuse", key="close_pdf_viewer"):
                    del st.session_state['_pdf_view']
                    st.rerun()

        # Affichage de la mémoire
        st.markdown("---")
        from app_ui import render_memory_display
        render_memory_display(st.session_state.mode)

    # Colonne de droite - Configuration
    with col_config:
        from app_ui import render_config_panel
        render_config_panel(config)

    # Footer
    st.markdown("---")
    st.caption(f"📁 Personnages: {st.session_state.char_dir} | 💾 Sessions: {st.session_state.config['paths']['save_dir']}")


if __name__ == "__main__":
    main()