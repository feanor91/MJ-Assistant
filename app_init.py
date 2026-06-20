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
        st.session_state.k_retrieval = config['rag']['k_retrieval']
        st.session_state.show_sources = config['ui']['show_sources_default']
        st.session_state.show_debug_chunks = config['rag'].get('debug_show_context', False)
        st.session_state.mode = config['ui']['default_mode']

        # Nouveau : Sélection des sources pour le mode encyclopédique
        st.session_state.encyclo_source_filter = "rules_and_universe"

        # Compteur pour auto-save
        st.session_state.message_count = 0
        st.session_state.auto_save_interval = config['ui'].get('auto_save_interval', 5)

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


def get_qa_chain(config, vectordb, model, mode, temp, top_p, k, show_sources, system_prompt, memory, short_memory, level, source_filter="rules_and_universe", query=""):
    """Crée la chaîne QA (doit être recréée à chaque requête car contient la mémoire)"""
    from core.rag import RAGChain

    rag_chain = RAGChain(config)

    # Filtrer les sources selon le mode
    if mode == "Encyclopédique":
        # Mode encyclopédique : filtrage selon le choix de l'utilisateur
        # ⚠️ Chroma utilise {"category": {"$in": [...]}} au lieu de $or
        if source_filter == "rules_only":
            # Option 1 : Règles uniquement (détaillées)
            filter_config = {
                "category": {"$in": ["rules", "unknown"]}
            }
        elif source_filter == "universe_only":
            # Option 2 : Univers uniquement (générales + romans)
            filter_config = {
                "category": {"$in": ["universe_book", "novel"]}
            }
        else:  # rules_and_universe (par défaut)
            # Option 3 : Règles + Univers (sans romans)
            filter_config = {
                "category": {"$in": ["rules", "universe_book", "unknown"]}
            }

        retriever = vectordb.as_retriever(
            search_kwargs={
                "k": k,
                "filter": filter_config
            }
        )
    else:
        # Mode MJ : tous les documents
        retriever = vectordb.as_retriever(search_kwargs={"k": k})

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


def process_query(query: str, config, mode: str, level: str, vectordb):
    """Traite une requête utilisateur"""
    try:
        # Prompt système
        system_prompt = config['prompts']['mj_system' if mode == "MJ immersif" else 'encyclo_system']

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

        # Récupérer le filtre de source pour le mode encyclopédique
        source_filter = st.session_state.get('encyclo_source_filter', 'rules_and_universe')

        # Créer la qa_chain avec tous les paramètres intégrés (y compris query pour re-ranking)
        qa_chain, _ = get_qa_chain(
            config=config,
            vectordb=vectordb,
            model=st.session_state.current_model,
            mode=mode,
            temp=temp_value,
            top_p=st.session_state.top_p,
            k=k_value,
            show_sources=st.session_state.show_sources,
            system_prompt=system_prompt,
            memory=memory_text,
            short_memory=short_memory_text,
            level=level,
            source_filter=source_filter,
            query=query  # 🆕 Passer la query pour le re-ranking
        )

        # Récupérer les documents via le retriever, puis invoquer la chaîne
        retriever = qa_chain["retriever"]
        format_context = qa_chain["format_context"]
        source_docs = retriever.invoke(query)
        context_text = format_context(source_docs)

        result = qa_chain["chain"].invoke({"context": context_text, "question": query})

        # 🔍 DEBUG : Afficher ce qui est retourné par le modèle
        print("\n" + "="*60)
        print("🔍 DEBUG - Résultat brut du modèle :")
        print("="*60)
        print("Type du résultat :", type(result))

        # Extraire la réponse (ChatMessage retourne .content)
        if hasattr(result, 'content'):
            response_text = result.content
        else:
            response_text = str(result)

        print("\n📝 Réponse extraite :")
        print("Longueur :", len(response_text), "caractères")
        print("Premiers 200 caractères :", response_text[:200])
        print("Nombre de sources :", len(source_docs))

        # 🔍 DEBUG supplémentaire si réponse vide
        if len(response_text) == 0:
            print("\n⚠️ ATTENTION : Réponse vide détectée !")
            print("Vérification du contexte envoyé au modèle...")
            if source_docs:
                print("\n📄 Aperçu des sources récupérées :")
                for i, doc in enumerate(source_docs[:3], 1):  # Premiers 3 chunks
                    print(f"\n--- Chunk {i} (source: {doc.metadata.get('source', 'inconnu')}) ---")
                    print(doc.page_content[:300])
                    print("...")
            else:
                print("❌ Aucune source récupérée ! Problème de recherche vectorielle.")

        print("="*60 + "\n")

        # Calculer la confiance basée sur les scores des documents
        if source_docs:
            scores = [doc.metadata.get("score", 0.5) for doc in source_docs]
            confidence = sum(scores) / len(scores) if scores else 0.5
        else:
            confidence = 0.0

        # Créer l'objet résultat
        result_obj = {
            "response": response_text,
            "sources": source_docs,
            "confidence": confidence
        }

        # Enregistrer dans la mémoire
        memory.add(query, result_obj['response'])

        # Parser la réponse (mode MJ uniquement)
        if mode == "MJ immersif":
            from core.parser import ResponseParser
            parsed = ResponseParser.parse(result_obj['response'])
            st.session_state.game_state.update_from_parsed(parsed)
            from datetime import datetime
            st.session_state.timeline.append({
                "query": query,
                "response": result_obj['response'],
                "timestamp": datetime.now().isoformat()
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
        raise e


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

    # Layout principal - colonne large pour le contenu principal, colonne droite pour la config
    col_main, col_config = st.columns([4, 1])

    # Colonne principale
    with col_main:
        # Timeline (mode MJ uniquement)
        if st.session_state.mode == "MJ immersif" and config['ui'].get('timeline_enabled', True):
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

        # Niveau de narration (mode MJ)
        if st.session_state.mode == "MJ immersif":
            level = st.selectbox(
                "Niveau de narration:",
                ["Résumé court", "Scène détaillée", "Longue narration immersive"],
                key="narration_level"
            )
        else:
            level = "N/A"

        # Utiliser un formulaire pour gérer l'envoi avec Entrée
        with st.form(key="query_form", clear_on_submit=True):
            user_query = st.text_input(
                "Ta question ou action (Entrée pour envoyer):",
                placeholder="Ex: Explique-moi le Voleur sans Mémoire",
                key="user_input"
            )

            # Avertissement pour questions trop larges
            if user_query and any(word in user_query.lower() for word in ["liste", "tous", "toutes", "22", "vingt"]):
                st.warning("⚠️ **Attention** : Les questions demandant des listes complètes peuvent générer des hallucinations. Le RAG fonctionne mieux avec des questions ciblées (ex: 'Explique l'arcane X').")

            # Bouton d'envoi
            submit = st.form_submit_button("📤 Envoyer", type="primary", use_container_width=True)

        # Traitement de la requête
        if submit and user_query and user_query.strip():
            with st.spinner("🤔 Le MJ réfléchit..."):
                try:
                    result = process_query(
                        query=user_query,
                        config=config,
                        mode=st.session_state.mode,
                        level=level,
                        vectordb=vectordb
                    )

                    # Marquer que la première requête a été envoyée
                    st.session_state.first_query_sent = True

                    # Afficher la question posée
                    st.markdown("### 💬 Question")
                    st.info(f"**{user_query}**")

                    # Affichage de la réponse
                    st.markdown("### ✅ Réponse")

                    if result['response'] and len(result['response'].strip()) > 0:
                        # Détection d'hallucination potentielle
                        suspicious_patterns = [
                            "une créature ou un lieu en danger",  # Répétition suspecte
                            "selon le contexte fourni",  # Phrase conclusive inventée
                            "Ce sont les",  # Phrase conclusive inventée
                        ]

                        hallucination_detected = False
                        for pattern in suspicious_patterns:
                            if result['response'].count(pattern) > 3:  # Répété plus de 3 fois = suspect
                                hallucination_detected = True
                                break

                        if hallucination_detected:
                            st.error("⚠️ ALERTE : Hallucination potentielle détectée !")
                            st.warning("""
                            Le modèle semble avoir **inventé** du contenu (répétitions suspectes détectées).

                            **Causes probables :**
                            - Les chunks récupérés ne contiennent pas l'information complète
                            - La question est trop large pour la recherche vectorielle

                            **Solutions :**
                            - Pose une question plus **ciblée** (ex: "Explique l'arcane 2")
                            - Vérifie les sources ci-dessous pour voir ce qui est réellement dans le contexte
                            - Augmente les chunks si nécessaire
                            """)

                            # Afficher la réponse suspecte
                            from app_ui import render_character_viewer_old
                            with st.expander("⚠️ Réponse suspecte (à vérifier)"):
                                st.markdown(result['response'])
                        else:
                            st.markdown(result['response'])
                    else:
                        st.error("❌ Le modèle n'a pas généré de réponse.")
                        st.warning("💡 **Causes possibles :**")
                        st.info("""
                        1. **Information incomplète** : Les chunks récupérés ne contiennent pas toute l'info demandée
                        2. **Trop peu de chunks** : Pour des questions larges (ex: "liste les 22 arcanes"), augmente le nombre de chunks
                        3. **Modèle trop strict** : Le modèle refuse de répondre partiellement

                        **Solutions :**
                        - ⬆️ Augmente le slider de chunks (essaie 30-50 pour des listes complètes)
                        - 🎯 Pose une question plus ciblée (ex: "explique l'arcane X")
                        - 🔄 Essaie un autre modèle (qwen2.5:14b ou mistral-nemo)
                        """)

                        # Afficher les sources pour aider au diagnostic
                        if st.session_state.get('show_sources', True) and result.get('sources'):
                            with st.expander("🔍 Sources récupérées (pour diagnostic)"):
                                st.caption(f"Le système a trouvé {len(result['sources'])} chunks. Vérifie s'ils contiennent l'information recherchée.")
                                for i, doc in enumerate(result['sources'][:5], 1):
                                    st.markdown(f"**Chunk {i}** (source: {doc.metadata.get('source', 'inconnu')})")
                                    preview = doc.page_content[:400].replace("\n", " ")
                                    st.text(preview + "...")
                                    st.markdown("---")

                    # Confiance RAG
                    if result['confidence'] > 0:
                        confidence_color = "🟢" if result['confidence'] > 0.7 else "🟡" if result['confidence'] > 0.4 else "🔴"
                        st.caption(f"{confidence_color} Confiance RAG: {result['confidence']:.0%}")

                    # Mode debug : afficher le contexte complet envoyé au modèle
                    if st.session_state.get('show_debug_chunks', False):
                        # Afficher quel filtre est actif
                        filter_names = {
                            "rules_only": "📖 Règles uniquement",
                            "universe_only": "🌍 Univers + Romans",
                            "rules_and_universe": "📖🌍 Règles + Univers (sans romans)"
                        }
                        current_source_filter = st.session_state.get('encyclo_source_filter', 'rules_and_universe')
                        active_filter = filter_names.get(current_source_filter, current_source_filter)

                        with st.expander(f"🔍 DEBUG: Chunks récupérés ({len(result['sources'])} chunks)"):
                            if result['sources']:
                                st.info(f"🎯 Filtre actif : **{active_filter}**")
                                st.warning("⚠️ Vérifiez si les informations recherchées sont présentes ci-dessous")
                                for i, doc in enumerate(result['sources'], 1):
                                    st.markdown(f"### Chunk {i}/{len(result['sources'])}")
                                    # Afficher les métadonnées
                                    if hasattr(doc, 'metadata') and doc.metadata:
                                        st.caption(f"Source: {doc.metadata.get('source', 'inconnu')} | Catégorie: {doc.metadata.get('category', 'inconnu')}")
                                    # Afficher le contenu complet
                                    st.text_area(f"Contenu chunk {i}", doc.page_content, height=200, key=f"debug_chunk_{i}")
                                    st.markdown("---")
                            else:
                                st.error("❌ Aucun chunk récupéré ! Problème de recherche RAG.")

                    # Sources (affichage normal)
                    if st.session_state.show_sources and result['sources']:
                        with st.expander(f"📚 Sources ({len(result['sources'])} documents)"):
                            for i, doc in enumerate(result['sources'], 1):
                                preview = doc.page_content[:400].replace("\n", " ")
                                st.markdown(f"**Source {i}:** {preview}...")

                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    import traceback
                    st.exception(traceback.format_exc())

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