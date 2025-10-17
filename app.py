"""
app.py
Application Streamlit principale - Assistant MJ Les Lames du Cardinal
"""

import sys
from pathlib import Path
from datetime import datetime
import time
import json

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

from core.rag import DocumentExtractor, VectorStore, RAGChain
from core.memory import Memory, SessionManager, Statistics
from core.parser import ResponseParser, GameState
from core.characters import CharacterManager
from core.utils import (
    load_config, get_ollama_models, validate_ollama_installation,
    export_session_to_markdown, ColorScheme
)


# =============================================================================
# CONFIGURATION ET INITIALISATION
# =============================================================================

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
    
    # Vérifier Ollama
    if not validate_ollama_installation():
        st.warning("⚠️ Ollama ne semble pas installé ou accessible.")
    
    return config


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
            st.session_state.statistics = Statistics()
        
        # Sessions
        st.session_state.session_manager = SessionManager(paths['save_dir'])
        
        # Personnages
        st.session_state.char_manager = CharacterManager(paths['char_dir'])
        
        # Paramètres UI
        st.session_state.current_model = config['model']['default']
        st.session_state.temperature = config['model']['temperature']
        st.session_state.top_p = config['model']['top_p']
        st.session_state.k_retrieval = config['rag']['k_retrieval']
        st.session_state.show_sources = config['ui']['show_sources_default']
        st.session_state.mode = config['ui']['default_mode']
        
        # Compteur pour auto-save
        st.session_state.message_count = 0
        st.session_state.auto_save_interval = config['ui'].get('auto_save_interval', 5)
        
        st.session_state.initialized = True


# =============================================================================
# INTERFACE UTILISATEUR
# =============================================================================

def render_sidebar(config):
    """Affiche la sidebar"""
    st.sidebar.title("⚙️ Configuration")
    
    # Sélection du modèle
    st.sidebar.subheader("Modèle")
    models = get_ollama_models()
    
    try:
        default_idx = models.index(st.session_state.current_model)
    except ValueError:
        default_idx = 0
    
    selected_model = st.sidebar.selectbox(
        "Choisir le modèle:",
        models,
        index=default_idx,
        key="model_selector"
    )
    
    if selected_model != st.session_state.current_model:
        st.session_state.current_model = selected_model
        # Invalider le cache QA
        if 'qa_chain' in st.session_state:
            del st.session_state['qa_chain']
    
    # Mode
    st.sidebar.subheader("Mode")
    mode = st.sidebar.radio(
        "Mode de jeu:",
        ["MJ immersif", "Encyclopédique"],
        index=0 if st.session_state.mode == "MJ immersif" else 1
    )
    st.session_state.mode = mode
    
    # Options d'affichage
    st.sidebar.subheader("Affichage")
    st.session_state.show_sources = st.sidebar.checkbox(
        "Afficher les sources RAG",
        value=st.session_state.show_sources
    )
    
    # Réglages experts
    st.sidebar.markdown("---")
    with st.sidebar.expander("🔧 Réglages experts"):
        st.session_state.temperature = st.slider(
            "Température",
            0.0, 1.5,
            st.session_state.temperature,
            0.05
        )
        st.session_state.top_p = st.slider(
            "Top P",
            0.0, 1.0,
            st.session_state.top_p,
            0.05
        )
        st.session_state.k_retrieval = st.slider(
            "Nombre de chunks RAG",
            1, 12,
            st.session_state.k_retrieval
        )
    
    # Gestion de la base vectorielle
    st.sidebar.markdown("---")
    st.sidebar.subheader("Base de données")
    
    col1, col2 = st.sidebar.columns(2)
    
    if col1.button("🔄 Recharger"):
        if 'vectordb' in st.session_state:
            del st.session_state['vectordb']
        st.cache_resource.clear()
        st.rerun()
    
    if col2.button("🗑️ Réinitialiser"):
        vector_store = VectorStore(config)
        vector_store.reset(config['paths']['db_dir'])
        # Supprimer aussi les métadonnées
        metadata_file = config['paths']['db_dir'] / "corpus_metadata.json"
        if metadata_file.exists():
            metadata_file.unlink()
        if 'vectordb' in st.session_state:
            del st.session_state['vectordb']
        st.cache_resource.clear()
        st.success("✅ Base réinitialisée")
        st.rerun()
    
    # Gestion des sessions
    render_session_manager()
    
    # Statistiques
    if config['advanced'].get('enable_statistics', True):
        render_statistics()
    
    # État du jeu (mode MJ uniquement)
    if mode == "MJ immersif":
        render_game_state()


def render_session_manager():
    """Affiche le gestionnaire de sessions"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 Sessions")
    
    session_manager = st.session_state.session_manager
    sessions = session_manager.list_sessions()
    
    # Sauvegarder
    session_name = st.sidebar.text_input(
        "Nom de session",
        value="default",
        key="session_name_input"
    )
    
    col1, col2 = st.sidebar.columns(2)
    
    if col1.button("💾 Sauver", use_container_width=True):
        success = session_manager.save_session(
            session_name=session_name,
            mj_memory=st.session_state.mj_memory,
            encyclo_memory=st.session_state.encyclo_memory,
            metadata={
                "game_state": st.session_state.game_state.to_dict(),
                "mode": st.session_state.mode,
                "model": st.session_state.current_model
            }
        )
        if success:
            st.sidebar.success(f"✅ Session '{session_name}' sauvegardée")
        else:
            st.sidebar.error("❌ Erreur lors de la sauvegarde")
    
    # Charger
    if sessions:
        selected_session = st.sidebar.selectbox(
            "Charger une session:",
            [""] + sessions,
            key="session_loader"
        )
        
        if col2.button("📂 Charger", use_container_width=True) and selected_session:
            data = session_manager.load_session(selected_session)
            if data:
                # Restaurer la mémoire
                st.session_state.mj_memory.entries = data['mj_entries']
                st.session_state.encyclo_memory.entries = data['encyclo_entries']
                
                # Restaurer l'état du jeu
                if 'game_state' in data.get('metadata', {}):
                    st.session_state.game_state.from_dict(data['metadata']['game_state'])
                
                # Restaurer les paramètres
                metadata = data.get('metadata', {})
                if 'mode' in metadata:
                    st.session_state.mode = metadata['mode']
                if 'model' in metadata:
                    st.session_state.current_model = metadata['model']
                
                st.sidebar.success(f"✅ Session '{selected_session}' chargée")
                st.rerun()
            else:
                st.sidebar.error("❌ Impossible de charger la session")
    
    # Export
    if st.sidebar.button("📄 Exporter en Markdown", use_container_width=True):
        export_path = st.session_state.config['paths']['save_dir'] / f"{session_name}_export.md"
        success = export_session_to_markdown(
            mj_memory=[e.to_dict() for e in st.session_state.mj_memory.entries],
            game_state=st.session_state.game_state.to_dict(),
            session_name=session_name,
            output_path=export_path
        )
        if success:
            st.sidebar.success(f"✅ Exporté vers {export_path.name}")
        else:
            st.sidebar.error("❌ Erreur lors de l'export")


def render_statistics():
    """Affiche les statistiques"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Statistiques")
    
    stats = st.session_state.statistics.get_summary()
    
    st.sidebar.metric("Requêtes totales", stats['total_queries'])
    st.sidebar.metric("Taux de succès", f"{stats['success_rate']:.1f}%")
    st.sidebar.metric("Durée session", stats['session_duration'])


def render_game_state():
    """Affiche l'état du jeu"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎮 État du jeu")
    
    game_state = st.session_state.game_state
    
    if game_state.npcs:
        st.sidebar.markdown("**PNJ:**")
        for name, status in list(game_state.npcs.items())[:5]:
            icon = game_state.get_npc_icon(status)
            st.sidebar.text(f"{icon} {name}")
    
    if game_state.locations:
        st.sidebar.markdown("**Lieux:**")
        for name, status in list(game_state.locations.items())[:5]:
            icon = game_state.get_location_icon(status)
            st.sidebar.text(f"{icon} {name}")
    
    if game_state.intrigues:
        st.sidebar.markdown("**Intrigues:**")
        for name, status in list(game_state.intrigues.items())[:3]:
            icon = game_state.get_intrigue_icon(status)
            st.sidebar.text(f"{icon} {name}")
    
    if st.sidebar.button("🗑️ Réinitialiser état", use_container_width=True):
        game_state.clear()
        st.rerun()


def render_timeline():
    """Affiche la timeline des actions"""
    if not st.session_state.timeline:
        st.info("Aucune action pour le moment. Commence à jouer!")
        return
    
    df = pd.DataFrame([
        {
            "Tour": f"Tour {i+1}",
            "Début": i,
            "Fin": i + 1,
            "Type": "Action"
        }
        for i in range(len(st.session_state.timeline))
    ])
    
    fig = px.timeline(
        df,
        x_start="Début",
        x_end="Fin",
        y="Tour",
        color="Type",
        color_discrete_map={"Action": "#8B0000"}
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=300, showlegend=False)
    
    st.plotly_chart(fig, use_container_width=True)


def render_character_viewer():
    """Affiche le visualiseur de fiches de personnages"""
    st.markdown("### 📇 Fiches de personnage")
    
    char_manager = st.session_state.char_manager
    char_manager.refresh()
    
    characters = char_manager.characters
    
    if not characters:
        st.info(f"Aucune fiche trouvée dans {st.session_state.char_dir}")
        st.caption("Dépose des fichiers .txt, .md ou .pdf dans ce dossier.")
        return
    
    # Sélection
    char_names = [""] + char_manager.get_character_names()
    selected = st.selectbox(
        "Choisir un personnage:",
        char_names,
        key="char_selector"
    )
    
    if selected:
        char = char_manager.get_character(selected)
        if char:
            # Vérifier si l'attribut is_pdf existe (compatibilité avec anciens objets)
            if not hasattr(char, 'is_pdf'):
                char.is_pdf = (char.file_path.suffix.lower() == ".pdf")
            
            # Affichage selon le type de fichier
            if char.is_pdf:
                # Affichage du PDF
                st.markdown(f"**Fichier PDF:** {char.file_path.name}")
                
                # Bouton pour ouvrir dans l'explorateur
                if st.button("📂 Ouvrir dans l'explorateur", key="open_pdf"):
                    import subprocess
                    import platform
                    if platform.system() == 'Windows':
                        subprocess.run(['explorer', str(char.file_path)])
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', str(char.file_path)])
                    else:  # Linux
                        subprocess.run(['xdg-open', str(char.file_path)])
                
                # Visualiseur PDF intégré
                try:
                    # Encoder le PDF en base64
                    import base64
                    with open(char.file_path, "rb") as f:
                        pdf_base64 = base64.b64encode(f.read()).decode()
                    
                    if pdf_base64:
                        pdf_display = f'''
                        <iframe src="data:application/pdf;base64,{pdf_base64}" 
                                width="100%" 
                                height="800" 
                                type="application/pdf"
                                style="border: 1px solid #ccc;">
                        </iframe>
                        '''
                        st.markdown(pdf_display, unsafe_allow_html=True)
                    else:
                        st.error("Impossible de charger le PDF")
                except Exception as e:
                    st.error(f"Erreur d'affichage du PDF: {e}")
                    st.info("Utilise le bouton ci-dessus pour ouvrir le fichier directement.")
                    
                    # Fallback: afficher le texte extrait
                    with st.expander("📄 Voir le texte extrait (moins lisible)"):
                        st.text_area(
                            "Contenu extrait",
                            value=char.content,
                            height=400,
                            key="char_content_fallback",
                            disabled=True
                        )
            else:
                # Affichage texte/markdown
                tabs = st.tabs(["📄 Contenu", "ℹ️ Info"])
                
                with tabs[0]:
                    st.text_area(
                        "Fiche (lecture seule)",
                        value=char.content,
                        height=500,
                        key="char_content",
                        disabled=True
                    )
                
                with tabs[1]:
                    st.write(f"**Fichier:** {char.file_path.name}")
                    st.write(f"**Chemin:** {char.file_path}")
                    st.write(f"**Taille:** {len(char.content)} caractères")


def render_memory_display(mode: str):
    """Affiche la mémoire selon le mode"""
    if mode == "MJ immersif":
        memory = st.session_state.mj_memory
        title = "🧾 Mémoire de la partie"
    else:
        memory = st.session_state.encyclo_memory
        title = "🧾 Historique des questions"
    
    if not memory:
        st.info("Aucun historique pour le moment.")
        return
    
    st.markdown(f"### {title}")
    
    # Afficher les derniers échanges
    recent = memory.get_recent(6)
    
    for i, entry in enumerate(reversed(recent), 1):
        with st.expander(f"Échange {len(memory) - i + 1}", expanded=(i == 1)):
            st.markdown(f"**Joueur:** {entry.user}")
            st.markdown(f"**Réponse:** {entry.assistant[:500]}{'...' if len(entry.assistant) > 500 else ''}")
            st.caption(f"_Horodatage: {entry.timestamp}_")
    
    # Bouton pour effacer
    if st.button("🗑️ Effacer l'historique", key="clear_memory"):
        memory.clear()
        if mode == "MJ immersif":
            st.session_state.timeline.clear()
        st.rerun()


# =============================================================================
# LOGIQUE PRINCIPALE
# =============================================================================

# =============================================================================
# LOGIQUE PRINCIPALE - Chargement intelligent
# =============================================================================

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
    
    with main_container.container():
        st.markdown("### ✅ Prêt")
        st.success("Base vectorielle chargée (aucun rechargement nécessaire)")
    
    import time
    time.sleep(1)
    main_container.empty()
    
    return vectordb


def get_qa_chain(config, vectordb, model, mode, temp, top_p, k, show_sources, system_prompt, memory, short_memory, level):
    """Crée la chaîne QA (doit être recréée à chaque requête car contient la mémoire)"""
    rag_chain = RAGChain(config)
    retriever = vectordb.as_retriever(search_kwargs={"k": k})
    
    qa_chain = rag_chain.create_qa_chain(
        retriever=retriever,
        model_name=model,
        mode="mj" if mode == "MJ immersif" else "encyclo",
        temperature=temp,
        top_p=top_p,
        return_sources=show_sources,
        system_prompt=system_prompt,
        memory=memory,
        short_memory=short_memory,
        level=level
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
        else:
            memory = st.session_state.encyclo_memory
            memory_text = ""
            short_memory_text = memory.format_for_prompt(
                n=config['memory']['short_memory_context'],
                prefix_user="Question",
                prefix_assistant="Réponse"
            )
        
        # Créer la qa_chain avec tous les paramètres intégrés
        qa_chain, _ = get_qa_chain(
            config=config,
            vectordb=vectordb,
            model=st.session_state.current_model,
            mode=mode,
            temp=st.session_state.temperature,
            top_p=st.session_state.top_p,
            k=st.session_state.k_retrieval,
            show_sources=st.session_state.show_sources,
            system_prompt=system_prompt,
            memory=memory_text,
            short_memory=short_memory_text,
            level=level
        )
        
        # Exécuter la requête (seulement avec query)
        result = qa_chain({"query": query})
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
            parsed = ResponseParser.parse(result_obj['response'])
            st.session_state.game_state.update_from_parsed(parsed)
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


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Fonction principale"""
    # Initialisation
    config = init_app()
    init_session_state(config)
    
    # CSS personnalisé
    st.markdown(ColorScheme.get_css(), unsafe_allow_html=True)
    
    # Titre
    st.title("🗡️ Assistant MJ - Les Lames du Cardinal")
    st.caption("RAG + Ollama | Mode immersif & Encyclopédique")
    
    # Sidebar
    render_sidebar(config)
    
    # Layout principal
    col_main, col_right = st.columns([3, 1.2])
    
    # Colonne principale
    with col_main:
        # Timeline (mode MJ uniquement)
        if st.session_state.mode == "MJ immersif" and config['ui'].get('timeline_enabled', True):
            st.markdown("### 🕰️ Timeline de la partie")
            render_timeline()
        
        # Chargement des documents et vectorstore - LOGIQUE INTELLIGENTE
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
            st.success(f"✅ **{reason}** - Chargement rapide activé !")
            
            # Charger uniquement la base vectorielle (ultra rapide)
            vectordb = load_vectorstore_only(config)
            
            # Lire les métadonnées pour afficher les stats
            metadata_file = config['paths']['db_dir'] / "corpus_metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        num_docs = metadata.get('total_files', 0)
                        st.info(f"📊 Base vectorielle contient {num_docs} documents")
                except Exception:
                    pass
        
        # Afficher stats finales (uniquement si on a rechargé)
        if needs_reload and 'documents' in locals():
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
        
        # Input utilisateur
        user_query = st.text_area(
            "Ta question ou action:",
            height=120,
            placeholder="Ex: Que se passe-t-il si j'ouvre cette porte ?\nEx: Explique-moi le système de combat.",
            key="user_input"
        )
        
        # Bouton d'envoi
        col_send, col_clear = st.columns([3, 1])
        
        with col_send:
            submit = st.button("📤 Envoyer", type="primary", use_container_width=True)
        
        with col_clear:
            if st.button("🗑️ Effacer", use_container_width=True):
                st.session_state.user_input = ""
                st.rerun()
        
        # Traitement de la requête
        if submit and user_query.strip():
            with st.spinner("🤔 Le MJ réfléchit..."):
                try:
                    result = process_query(
                        query=user_query,
                        config=config,
                        mode=st.session_state.mode,
                        level=level,
                        vectordb=vectordb
                    )
                    
                    # Affichage de la réponse
                    st.markdown("### ✅ Réponse")
                    st.markdown(result['response'])
                    
                    # Confiance RAG
                    if result['confidence'] > 0:
                        confidence_color = "🟢" if result['confidence'] > 0.7 else "🟡" if result['confidence'] > 0.4 else "🔴"
                        st.caption(f"{confidence_color} Confiance RAG: {result['confidence']:.0%}")
                    
                    # Sources
                    if st.session_state.show_sources and result['sources']:
                        with st.expander(f"📚 Sources ({len(result['sources'])} documents)"):
                            for i, doc in enumerate(result['sources'], 1):
                                preview = doc.page_content[:400].replace("\n", " ")
                                st.markdown(f"**Source {i}:** {preview}...")
                
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
                    st.exception(e)
        
        # Affichage de la mémoire
        st.markdown("---")
        render_memory_display(st.session_state.mode)
    
    # Colonne de droite - Personnages
    with col_right:
        render_character_viewer()
    
    # Footer
    st.markdown("---")
    st.caption(f"📁 Personnages: {st.session_state.char_dir} | 💾 Sessions: {st.session_state.config['paths']['save_dir']}")


if __name__ == "__main__":
    main()