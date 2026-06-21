"""
app.py
Application Streamlit principale - Assistant MJ Les Lames du Cardinal
"""

import sys
from pathlib import Path
from datetime import datetime
import time
import json
import warnings
import logging

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

# Supprimer les warnings PDF embêtants
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("PyPDF2").setLevel(logging.ERROR)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

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
        st.session_state.show_debug_chunks = config['rag'].get('debug_show_context', False)
        st.session_state.mode = config['ui']['default_mode']

        # Nouveau : Sélection des sources pour le mode encyclopédique
        st.session_state.encyclo_source_filter = "rules_and_universe"  # Par défaut : Règles + Univers
        
        # Compteur pour auto-save
        st.session_state.message_count = 0
        st.session_state.auto_save_interval = config['ui'].get('auto_save_interval', 5)

        st.session_state.initialized = True


# =============================================================================
# INTERFACE UTILISATEUR
# =============================================================================

def render_sidebar():
    """Affiche la sidebar avec les fiches de personnages"""
    st.sidebar.title("📇 Fiches de personnage")

    char_manager = st.session_state.char_manager
    char_manager.refresh()

    characters = char_manager.characters

    if not characters:
        st.sidebar.info(f"Aucune fiche trouvée dans {st.session_state.char_dir}")
        st.sidebar.caption("Dépose des fichiers .txt, .md ou .pdf dans ce dossier.")
        return

    # Sélection - SAUVEGARDER la sélection dans session_state
    char_names = [""] + char_manager.get_character_names()

    # Récupérer la dernière sélection
    default_index = 0
    if 'selected_character' in st.session_state:
        try:
            default_index = char_names.index(st.session_state.selected_character)
        except ValueError:
            default_index = 0

    selected = st.sidebar.selectbox(
        "Choisir un personnage:",
        char_names,
        index=default_index,
        key="char_selector"
    )

    # Sauvegarder la sélection
    if selected:
        st.session_state.selected_character = selected

    st.sidebar.markdown("---")

    if selected:
        char = char_manager.get_character(selected)
        if char:
            # Vérifier si l'attribut is_pdf existe (compatibilité avec anciens objets)
            if not hasattr(char, 'is_pdf'):
                char.is_pdf = (char.file_path.suffix.lower() == ".pdf")

            # Affichage selon le type de fichier
            if char.is_pdf:
                # Affichage du PDF
                st.sidebar.markdown(f"**📄 Fichier:** {char.file_path.name}")

                col1, col2 = st.sidebar.columns([1, 1])

                with col1:
                    # Bouton pour ouvrir dans l'explorateur
                    if st.button("📂 Ouvrir", key="open_pdf", use_container_width=True):
                        import subprocess
                        import platform
                        if platform.system() == 'Windows':
                            import os
                            os.startfile(str(char.file_path))
                        elif platform.system() == 'Darwin':  # macOS
                            subprocess.run(['open', str(char.file_path)])
                        else:  # Linux
                            subprocess.run(['xdg-open', str(char.file_path)])

                with col2:
                    # Bouton de téléchargement
                    try:
                        with open(char.file_path, "rb") as f:
                            pdf_bytes = f.read()
                        st.download_button(
                            label="💾 Télécharger",
                            data=pdf_bytes,
                            file_name=char.file_path.name,
                            mime="application/pdf",
                            key="download_pdf",
                            use_container_width=True
                        )
                    except Exception:
                        pass

                st.sidebar.markdown("---")

                # Visualiseur PDF dans la sidebar - convertir en image avec pdf2image
                try:
                    # Initialiser la page courante
                    if 'pdf_page' not in st.session_state:
                        st.session_state.pdf_page = 1

                    # Compter les pages et convertir en images
                    try:
                        from pdf2image import convert_from_path
                        from PIL import Image
                        import PyPDF2
                        import os
                        import contextlib

                        # Supprimer les messages d'erreur PDF en redirigeant stderr
                        @contextlib.contextmanager
                        def suppress_stderr():
                            """Supprime temporairement les messages stderr"""
                            devnull = open(os.devnull, 'w')
                            old_stderr = sys.stderr
                            sys.stderr = devnull
                            try:
                                yield
                            finally:
                                sys.stderr = old_stderr
                                devnull.close()

                        # Compter le nombre de pages (sans les warnings)
                        with suppress_stderr():
                            with open(char.file_path, "rb") as f:
                                pdf_reader = PyPDF2.PdfReader(f)
                                total_pages = len(pdf_reader.pages)

                        # S'assurer que la page courante est valide
                        if st.session_state.pdf_page > total_pages:
                            st.session_state.pdf_page = total_pages
                        if st.session_state.pdf_page < 1:
                            st.session_state.pdf_page = 1

                        # Contrôles de navigation dans la sidebar
                        col_prev, col_info, col_next = st.sidebar.columns([1, 2, 1])

                        with col_prev:
                            if st.button("◀", key="pdf_prev", use_container_width=True, disabled=(st.session_state.pdf_page <= 1)):
                                st.session_state.pdf_page -= 1
                                st.rerun()

                        with col_info:
                            st.markdown(f"<center>Page {st.session_state.pdf_page}/{total_pages}</center>", unsafe_allow_html=True)

                        with col_next:
                            if st.button("▶", key="pdf_next", use_container_width=True, disabled=(st.session_state.pdf_page >= total_pages)):
                                st.session_state.pdf_page += 1
                                st.rerun()

                        # Convertir uniquement la page courante en image (plus rapide)
                        # DPI 200 pour une bonne qualité

                        # Chemin Poppler
                        poppler_path = r"D:\IA\poppler-25.07.0\Library\bin"

                        # Convertir la page en image (sans les warnings)
                        with suppress_stderr():
                            # Vérifier si Poppler existe à cet endroit
                            if os.path.exists(poppler_path):
                                images = convert_from_path(
                                    str(char.file_path),
                                    dpi=200,
                                    first_page=st.session_state.pdf_page,
                                    last_page=st.session_state.pdf_page,
                                    poppler_path=poppler_path
                                )
                            else:
                                # Essayer sans spécifier le chemin (au cas où Poppler est dans le PATH)
                                images = convert_from_path(
                                    str(char.file_path),
                                    dpi=200,
                                    first_page=st.session_state.pdf_page,
                                    last_page=st.session_state.pdf_page
                                )

                        if images:
                            # Afficher l'image dans la sidebar
                            st.sidebar.image(images[0], use_container_width=True)

                    except ImportError as e:
                        st.sidebar.error(f"❌ Import Error: {e}")
                        st.sidebar.info("1. Installe pdf2image: pip install pdf2image")
                        st.sidebar.info("2. Vérifie que Poppler est dans: D:\\IA\\poppler-25.07.0\\Library\\bin")
                        st.sidebar.info("💡 En attendant, utilise le bouton 'Ouvrir' ci-dessus.")
                    except Exception as e:
                        st.sidebar.error(f"❌ Erreur détaillée: {type(e).__name__}: {e}")
                        st.sidebar.code(f"Chemin Poppler: {poppler_path}")
                        st.sidebar.code(f"Poppler existe: {os.path.exists(poppler_path)}")
                        st.sidebar.info("💡 Utilise le bouton 'Ouvrir' ci-dessus.")

                except Exception as e:
                    st.sidebar.error(f"❌ Erreur: {e}")
                    st.sidebar.info("💡 Utilise le bouton 'Ouvrir' ci-dessus.")
            else:
                # Affichage texte/markdown
                st.sidebar.text_area(
                    "Fiche (lecture seule)",
                    value=char.content,
                    height=600,
                    key="char_content_sidebar",
                    disabled=True
                )


def render_config_panel(config):
    """Affiche le panneau de configuration dans la colonne de droite"""
    st.markdown("### ⚙️ Configuration")

    # Sélection du modèle
    st.markdown("**Modèle**")
    models = get_ollama_models()

    try:
        default_idx = models.index(st.session_state.current_model)
    except ValueError:
        default_idx = 0

    selected_model = st.selectbox(
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
    st.markdown("**Mode**")
    mode = st.radio(
        "Mode de jeu:",
        ["MJ immersif", "Encyclopédique"],
        index=0 if st.session_state.mode == "MJ immersif" else 1
    )
    st.session_state.mode = mode

    if mode == "Encyclopédique":
        rerank_enabled = config['rag'].get('enable_reranking', False)
        if rerank_enabled:
            st.info("📚 Mode encyclopédique | Re-ranking activé")
        else:
            st.info("📚 Mode encyclopédique")

    # Gestion des sessions
    st.markdown("---")
    render_session_manager()

    # Statistiques
    if config['advanced'].get('enable_statistics', True):
        st.markdown("---")
        render_statistics()

    # État du jeu (mode MJ uniquement)
    if mode == "MJ immersif":
        st.markdown("---")
        render_game_state()


def render_session_manager():
    """Affiche le gestionnaire de sessions"""
    st.markdown("**💾 Sessions**")

    session_manager = st.session_state.session_manager
    sessions = session_manager.list_sessions()

    # Sauvegarder
    session_name = st.text_input(
        "Nom de session",
        value="default",
        key="session_name_input"
    )

    col1, col2 = st.columns(2)

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
            st.success(f"✅ Session '{session_name}' sauvegardée")
        else:
            st.error("❌ Erreur lors de la sauvegarde")

    # Charger
    if sessions:
        selected_session = st.selectbox(
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

                st.success(f"✅ Session '{selected_session}' chargée")
                st.rerun()
            else:
                st.error("❌ Impossible de charger la session")

    # Export
    if st.button("📄 Exporter en Markdown", use_container_width=True):
        export_path = st.session_state.config['paths']['save_dir'] / f"{session_name}_export.md"
        success = export_session_to_markdown(
            mj_memory=[e.to_dict() for e in st.session_state.mj_memory.entries],
            game_state=st.session_state.game_state.to_dict(),
            session_name=session_name,
            output_path=export_path
        )
        if success:
            st.success(f"✅ Exporté vers {export_path.name}")
        else:
            st.error("❌ Erreur lors de l'export")


def render_statistics():
    """Affiche les statistiques"""
    st.markdown("**📊 Statistiques**")

    stats = st.session_state.statistics.get_summary()

    col1, col2, col3 = st.columns(3)
    col1.metric("Requêtes", stats['total_queries'])
    col2.metric("Succès", f"{stats['success_rate']:.1f}%")
    col3.metric("Durée", stats['session_duration'])


def render_game_state():
    """Affiche l'état du jeu"""
    st.markdown("**🎮 État du jeu**")

    game_state = st.session_state.game_state

    if game_state.npcs:
        st.markdown("**PNJ:**")
        for name, status in list(game_state.npcs.items())[:5]:
            icon = game_state.get_npc_icon(status)
            st.text(f"{icon} {name}")

    if game_state.locations:
        st.markdown("**Lieux:**")
        for name, status in list(game_state.locations.items())[:5]:
            icon = game_state.get_location_icon(status)
            st.text(f"{icon} {name}")

    if game_state.intrigues:
        st.markdown("**Intrigues:**")
        for name, status in list(game_state.intrigues.items())[:3]:
            icon = game_state.get_intrigue_icon(status)
            st.text(f"{icon} {name}")

    if st.button("🗑️ Réinitialiser état", use_container_width=True):
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


def render_character_viewer_old():
    """Affiche le visualiseur de fiches de personnages"""

    st.markdown("### 📇 Fiches de personnage")

    char_manager = st.session_state.char_manager
    char_manager.refresh()

    characters = char_manager.characters

    if not characters:
        st.info(f"Aucune fiche trouvée dans {st.session_state.char_dir}")
        st.caption("Dépose des fichiers .txt, .md ou .pdf dans ce dossier.")
        return

    # Sélection - SAUVEGARDER la sélection dans session_state
    char_names = [""] + char_manager.get_character_names()

    # Récupérer la dernière sélection
    default_index = 0
    if 'selected_character' in st.session_state:
        try:
            default_index = char_names.index(st.session_state.selected_character)
        except ValueError:
            default_index = 0

    selected = st.selectbox(
        "Choisir un personnage:",
        char_names,
        index=default_index,
        key="char_selector"
    )

    # Sauvegarder la sélection
    if selected:
        st.session_state.selected_character = selected

    st.markdown("---")
    
    if selected:
        char = char_manager.get_character(selected)
        if char:
            # Vérifier si l'attribut is_pdf existe (compatibilité avec anciens objets)
            if not hasattr(char, 'is_pdf'):
                char.is_pdf = (char.file_path.suffix.lower() == ".pdf")
            
            # Affichage selon le type de fichier
            if char.is_pdf:
                # Affichage du PDF
                st.markdown(f"**📄 Fichier:** {char.file_path.name}")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Bouton pour ouvrir dans l'explorateur
                    if st.button("📂 Ouvrir dans lecteur PDF", key="open_pdf", use_container_width=True):
                        import subprocess
                        import platform
                        if platform.system() == 'Windows':
                            import os
                            os.startfile(str(char.file_path))
                        elif platform.system() == 'Darwin':  # macOS
                            subprocess.run(['open', str(char.file_path)])
                        else:  # Linux
                            subprocess.run(['xdg-open', str(char.file_path)])
                
                with col2:
                    # Bouton de téléchargement
                    try:
                        with open(char.file_path, "rb") as f:
                            pdf_bytes = f.read()
                        st.download_button(
                            label="💾 Télécharger le PDF",
                            data=pdf_bytes,
                            file_name=char.file_path.name,
                            mime="application/pdf",
                            key="download_pdf",
                            use_container_width=True
                        )
                    except Exception:
                        pass
                
                st.markdown("---")
                
                # Visualiseur PDF avec PDF.js
                try:
                    import base64
                    with open(char.file_path, "rb") as f:
                        pdf_bytes = f.read()
                        pdf_base64 = base64.b64encode(pdf_bytes).decode()
                    
                    st.markdown("#### 📖 Aperçu du document")
                    
                    # Utiliser PDF.js pour le rendu
                    pdf_viewer_html = f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body {{
                                margin: 0;
                                padding: 0;
                                overflow: hidden;
                            }}
                            #pdf-container {{
                                width: 100%;
                                height: 800px;
                                overflow: auto;
                                border: 2px solid #ddd;
                                border-radius: 5px;
                                background: #525659;
                            }}
                            canvas {{
                                display: block;
                                margin: 10px auto;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                            }}
                            .controls {{
                                position: sticky;
                                top: 0;
                                background: white;
                                padding: 10px;
                                border-bottom: 2px solid #ddd;
                                text-align: center;
                                z-index: 100;
                            }}
                            button {{
                                margin: 0 5px;
                                padding: 8px 16px;
                                background: #8B0000;
                                color: white;
                                border: none;
                                border-radius: 4px;
                                cursor: pointer;
                                font-size: 14px;
                            }}
                            button:hover {{
                                background: #A00000;
                            }}
                            #page-info {{
                                display: inline-block;
                                margin: 0 10px;
                                font-weight: bold;
                            }}
                        </style>
                        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
                    </head>
                    <body>
                        <div id="pdf-container">
                            <div class="controls">
                                <button id="prev-page">◀ Précédent</button>
                                <span id="page-info">Page <span id="page-num">1</span> / <span id="page-count">?</span></span>
                                <button id="next-page">Suivant ▶</button>
                                <button id="zoom-in">🔍 Zoom +</button>
                                <button id="zoom-out">🔍 Zoom -</button>
                            </div>
                            <canvas id="pdf-canvas"></canvas>
                        </div>
                        
                        <script>
                            const pdfData = atob('{pdf_base64}');
                            const pdfBytes = new Uint8Array(pdfData.length);
                            for (let i = 0; i < pdfData.length; i++) {{
                                pdfBytes[i] = pdfData.charCodeAt(i);
                            }}
                            
                            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                            
                            let pdfDoc = null;
                            let pageNum = 1;
                            let pageRendering = false;
                            let pageNumPending = null;
                            let scale = 1.5;
                            const canvas = document.getElementById('pdf-canvas');
                            const ctx = canvas.getContext('2d');
                            
                            function renderPage(num) {{
                                pageRendering = true;
                                pdfDoc.getPage(num).then(function(page) {{
                                    const viewport = page.getViewport({{scale: scale}});
                                    canvas.height = viewport.height;
                                    canvas.width = viewport.width;
                                    
                                    const renderContext = {{
                                        canvasContext: ctx,
                                        viewport: viewport
                                    }};
                                    
                                    const renderTask = page.render(renderContext);
                                    renderTask.promise.then(function() {{
                                        pageRendering = false;
                                        if (pageNumPending !== null) {{
                                            renderPage(pageNumPending);
                                            pageNumPending = null;
                                        }}
                                    }});
                                }});
                                
                                document.getElementById('page-num').textContent = num;
                            }}
                            
                            function queueRenderPage(num) {{
                                if (pageRendering) {{
                                    pageNumPending = num;
                                }} else {{
                                    renderPage(num);
                                }}
                            }}
                            
                            function onPrevPage() {{
                                if (pageNum <= 1) return;
                                pageNum--;
                                queueRenderPage(pageNum);
                            }}
                            
                            function onNextPage() {{
                                if (pageNum >= pdfDoc.numPages) return;
                                pageNum++;
                                queueRenderPage(pageNum);
                            }}
                            
                            function onZoomIn() {{
                                scale += 0.25;
                                queueRenderPage(pageNum);
                            }}
                            
                            function onZoomOut() {{
                                if (scale <= 0.5) return;
                                scale -= 0.25;
                                queueRenderPage(pageNum);
                            }}
                            
                            document.getElementById('prev-page').addEventListener('click', onPrevPage);
                            document.getElementById('next-page').addEventListener('click', onNextPage);
                            document.getElementById('zoom-in').addEventListener('click', onZoomIn);
                            document.getElementById('zoom-out').addEventListener('click', onZoomOut);
                            
                            pdfjsLib.getDocument({{data: pdfBytes}}).promise.then(function(pdf) {{
                                pdfDoc = pdf;
                                document.getElementById('page-count').textContent = pdf.numPages;
                                renderPage(pageNum);
                            }});
                        </script>
                    </body>
                    </html>
                    '''
                    
                    # Afficher le viewer avec composant HTML
                    import streamlit.components.v1 as components
                    components.html(pdf_viewer_html, height=850, scrolling=False)
                    
                except Exception as e:
                    st.error(f"❌ Erreur d'affichage du PDF: {e}")
                    st.info("💡 Utilise le bouton 'Ouvrir dans lecteur PDF' ci-dessus.")
                    
                    # Fallback: afficher le texte extrait
                    with st.expander("📄 Voir le texte extrait (moins lisible)"):
                        st.text_area(
                            "Contenu extrait",
                            value=char.content[:5000] + ("..." if len(char.content) > 5000 else ""),
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
    from core.rag import DocumentExtractor
    from langchain_community.vectorstores import Chroma
    
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
        
        # Exécuter la requête (utilise invoke au lieu de __call__)
        result = qa_chain.invoke({"query": query})

        # 🔍 DEBUG : Afficher ce qui est retourné par le modèle
        print("\n" + "="*60)
        print("🔍 DEBUG - Résultat brut du modèle :")
        print("="*60)
        print("Type du résultat :", type(result))
        print("Clés disponibles :", result.keys() if isinstance(result, dict) else "N/A")

        # Extraire les valeurs du résultat
        response_text = result.get("result", result.get("answer", ""))
        source_docs = result.get("source_documents", [])

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

    # Titre tout en haut pour maximiser l'espace
    st.title("🗡️ Les Lames du Cardinal")

    # Sidebar avec les fiches de personnages
    render_sidebar()

    # Layout principal - colonne large pour le contenu principal, colonne droite pour la config
    col_main, col_config = st.columns([4, 1])
    
    # Colonne principale
    with col_main:
        # Timeline (mode MJ uniquement)
        if st.session_state.mode == "MJ immersif" and config['ui'].get('timeline_enabled', True):
            st.markdown("### 🕰️ Timeline de la partie")
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

            # Lire les métadonnées pour afficher les stats
            if not st.session_state.first_query_sent:
                metadata_file = config['paths']['db_dir'] / "corpus_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
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
                    st.exception(e)
        
        # Affichage de la mémoire
        st.markdown("---")
        render_memory_display(st.session_state.mode)

    # Colonne de droite - Configuration
    with col_config:
        render_config_panel(config)

    # Footer
    st.markdown("---")
    st.caption(f"📁 Personnages: {st.session_state.char_dir} | 💾 Sessions: {st.session_state.config['paths']['save_dir']}")


if __name__ == "__main__":
    main()