"""
app.py
Application Streamlit principale - Assistant MJ Les Lames du Cardinal
"""

import sys
from pathlib import Path

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
        st.rerun()
    
    if col2.button("🗑️ Réinitialiser"):
        vector_store = VectorStore(config)
        vector_store.reset(st.session_state.db_dir)
        if 'vectordb' in st.session_state:
            del st.session_state['vectordb']
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
            # Affichage avec options
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

@st.cache_resource
def load_documents(_config):
    """Charge les documents (cached)"""
    extractor = DocumentExtractor()
    max_pages = _config['advanced'].get('max_pdf_pages')
    return extractor.extract_from_directory(_config['paths']['pdf_root'], max_pages)


@st.cache_resource
def build_vectorstore(_config, _documents):
    """Construit le vectorstore (cached)"""
    vector_store = VectorStore(_config)
    return vector_store.build_or_load(_documents, _config['paths']['db_dir'])


def get_qa_chain(config, vectordb, model, mode, temp, top_p, k, show_sources):
    """Crée ou récupère la chaîne QA (avec cache manuel intelligent)"""
    # Clé de cache basée sur tous les paramètres
    cache_key = f"{model}_{mode}_{temp}_{top_p}_{k}_{show_sources}"
    
    if 'qa_chain_cache_key' not in st.session_state or st.session_state.qa_chain_cache_key != cache_key:
        # Recréer la chaîne
        rag_chain = RAGChain(config)
        retriever = vectordb.as_retriever(search_kwargs={"k": k})
        
        qa_chain = rag_chain.create_qa_chain(
            retriever=retriever,
            model_name=model,
            mode="mj" if mode == "MJ immersif" else "encyclo",
            temperature=temp,
            top_p=top_p,
            return_sources=show_sources
        )
        
        st.session_state.qa_chain = qa_chain
        st.session_state.qa_chain_cache_key = cache_key
        st.session_state.rag_chain = rag_chain
    
    return st.session_state.qa_chain, st.session_state.rag_chain


def process_query(query: str, config, qa_chain, rag_chain, mode: str, level: str = "N/A"):
    """Traite une requête utilisateur"""
    try:
        # Préparer les paramètres
        if mode == "MJ immersif":
            memory = st.session_state.mj_memory
            memory_text = memory.format_for_prompt(n=config['memory']['short_memory_context'])
            short_memory = ""
        else:
            memory = st.session_state.encyclo_memory
            memory_text = ""
            short_memory = memory.format_for_prompt(
                n=config['memory']['short_memory_context'],
                prefix_user="Question",
                prefix_assistant="Réponse"
            )
        
        # Prompt système
        system_prompt = config['prompts']['mj_system' if mode == "MJ immersif" else 'encyclo_system']
        
        # Exécuter la requête
        result = rag_chain.query(
            qa_chain=qa_chain,
            question=query,
            mode="mj" if mode == "MJ immersif" else "encyclo",
            system_prompt=system_prompt,
            memory=memory_text,
            level=level,
            short_memory=short_memory
        )
        
        # Enregistrer dans la mémoire
        memory.add(query, result['response'])
        
        # Parser la réponse (mode MJ uniquement)
        if mode == "MJ immersif":
            parsed = ResponseParser.parse(result['response'])
            st.session_state.game_state.update_from_parsed(parsed)
            st.session_state.timeline.append({
                "query": query,
                "response": result['response'],
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
        
        return result
    
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
        
        # Chargement des documents et vectorstore
        with st.spinner("🔄 Chargement du corpus..."):
            documents = load_documents(config)
            
            if not documents:
                st.warning(f"⚠️ Aucun document trouvé dans {config['paths']['pdf_root']}")
                st.info("Dépose tes PDFs de règles dans ce dossier.")
                st.stop()
            
            vectordb = build_vectorstore(config, documents)
            
            # QA Chain
            qa_chain, rag_chain = get_qa_chain(
                config=config,
                vectordb=vectordb,
                model=st.session_state.current_model,
                mode=st.session_state.mode,
                temp=st.session_state.temperature,
                top_p=st.session_state.top_p,
                k=st.session_state.k_retrieval,
                show_sources=st.session_state.show_sources
            )
        
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
                        qa_chain=qa_chain,
                        rag_chain=rag_chain,
                        mode=st.session_state.mode,
                        level=level
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