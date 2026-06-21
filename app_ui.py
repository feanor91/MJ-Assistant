"""
app_ui.py
Interface utilisateur de l'application
"""

import sys
import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px


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
                        _poppler = locals().get('poppler_path', r"D:\IA\poppler-25.07.0\Library\bin")
                        st.sidebar.code(f"Chemin Poppler: {_poppler}")
                        st.sidebar.code(f"Poppler existe: {os.path.exists(_poppler)}")
                        st.sidebar.info("💡 Utilise le bouton 'Ouvrir' ci-dessus.")

                except Exception as e:
                    st.sidebar.error(f"❌ Erreur: {e}")
                    st.sidebar.info("💡 Utilise le bouton 'Ouvrir' ci-dessus.")
            else:
                # Affichage texte/markdown
                st.text_area(
                    "Fiche (lecture seule)",
                    value=char.content,
                    height=300,
                    key=f"fiche_{char.file_path.name}",
                    disabled=True
                )

        # Info supplémentaire
        st.sidebar.markdown("---")
        try:
            with open(char.file_path, 'r', encoding='utf-8') as f:
                import json
                try:
                    content = json.load(f)
                    if isinstance(content, dict):
                        with st.sidebar.expander("ℹ️ Info fiche"):
                            st.json(content)
                except:
                    pass
        except Exception:
            pass


def render_timeline():
    """Affiche la timeline de la partie (tous modes, color-codée)"""
    if not st.session_state.timeline:
        return

    # Couleurs et icônes par mode
    _MODE_STYLE = {
        "MJ immersif":   {"icon": "🗡️", "color": "#4a90d9", "label": "MJ immersif"},
        "Narratif pur":  {"icon": "✨", "color": "#9b59b6", "label": "Narratif pur"},
        "Encyclopédique":{"icon": "📚", "color": "#27ae60", "label": "Encyclopédique"},
    }
    _DEFAULT_STYLE = {"icon": "💬", "color": "#888888", "label": "?"}

    st.markdown("### 🕰️ Timeline de la partie")
    with st.expander("Voir la timeline"):
        total = len(st.session_state.timeline)
        for i, entry in enumerate(reversed(st.session_state.timeline)):
            entry_mode = entry.get('mode', 'MJ immersif')
            style = _MODE_STYLE.get(entry_mode, _DEFAULT_STYLE)
            idx = total - i

            color = style['color']
            icon  = style['icon']
            label = style['label']
            ts    = entry['timestamp'][:16]

            with st.expander(f"{icon} #{idx} {label}", expanded=(i == 0)):
                st.markdown(
                    f"<div style='border-left:3px solid {color};"
                    f"padding-left:10px;margin-bottom:8px;'>"
                    f"<b>Joueur :</b> {entry['query']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(entry['response'])
                st.caption(f"_{entry['timestamp']}_")


_EXCLUDED = {
    "bge-m3:latest", "mxbai-embed-large:latest",
    "minimax-m2:cloud",
    "phi3:3.8b", "llama3.2:latest",
    "glm-4.7-flash:latest",
}

_LABELS = {
    "qwen3.6:35b-a3b":                    "Narration immersive — meilleure qualité",
    "mistral-nemo:latest":                 "Narration FR — recommandé",
    "maxwellb/gemma4-12b-it-oym:latest":   "Narration / Polyvalent",
    "qwen2.5:14b":                         "Règles précises / Encyclopédique",
    "phi4:latest":                         "Règles précises / Structuré",
    "phi3:14b":                            "Polyvalent / Rapide",
    "mistral:latest":                      "Rapide / Léger",
    "llama3:latest":                       "Polyvalent",
    "gpt-oss:latest":                      "Polyvalent",
}

# Modèles préférés par mode (ordre de priorité)
_MODE_PRESETS = {
    "MJ immersif": {
        "model_priority": [
            "mistral-nemo:latest",
            "maxwellb/gemma4-12b-it-oym:latest",
            "qwen3.6:35b-a3b",
            "mistral:latest",
        ],
        "temperature": 0.8,
        "top_p": 0.95,
        "k_retrieval": 10,
        "show_sources": False,
    },
    "Encyclopédique": {
        "model_priority": [
            "mistral-nemo:latest",
            "qwen2.5:14b",
            "phi4:latest",
            "phi3:14b",
        ],
        "temperature": 0.0,
        "top_p": 0.9,
        "k_retrieval_encyclo": 8,
        "source_filter": "rules_and_universe",
        "show_sources": True,
    },
}


def _preload_model_bg(model_name: str):
    """Charge le modèle en mémoire GPU via l'API Ollama (thread background)."""
    import threading
    import urllib.request
    import json as _json

    def _load():
        try:
            payload = _json.dumps({
                "model": model_name,
                "keep_alive": -1   # Garder en mémoire indéfiniment
            }).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                resp.read()
            print(f"✅ Modèle {model_name} chargé en mémoire GPU")
        except Exception as e:
            print(f"⚠️ Préchargement {model_name} impossible : {e}")

    threading.Thread(target=_load, daemon=True).start()


def _apply_mode_presets(mode: str, available_models: list):
    """Applique les réglages par défaut pour un mode donné."""
    preset = _MODE_PRESETS.get(mode)
    if not preset:
        return

    # Modèle : premier disponible dans la liste de priorité
    chosen = next(
        (m for m in preset["model_priority"] if m in available_models),
        available_models[0] if available_models else None
    )
    if chosen:
        st.session_state.current_model = chosen
        # Précharger immédiatement si le modèle change via preset
        if chosen != st.session_state.get("_last_preloaded_model"):
            _preload_model_bg(chosen)
            st.session_state._last_preloaded_model = chosen

    # Température
    st.session_state.temperature = preset["temperature"]
    st.session_state.temp_slider = preset["temperature"]

    # Top-p
    st.session_state.top_p = preset["top_p"]
    st.session_state.top_p_slider = preset["top_p"]

    # Affichage des sources
    if "show_sources" in preset:
        st.session_state.show_sources = preset["show_sources"]
        st.session_state.show_sources_checkbox = preset["show_sources"]

    # Réinitialiser le toggle narratif pur (appelé avant le rendu du toggle)
    st.session_state.creative_mode = False

    # Réglages spécifiques au mode
    if mode == "MJ immersif":
        st.session_state.k_retrieval = preset["k_retrieval"]
        st.session_state.k_mj_slider = preset["k_retrieval"]
    elif mode == "Encyclopédique":
        st.session_state.encyclo_k_retrieval = preset["k_retrieval_encyclo"]
        st.session_state.k_retrieval_slider = preset["k_retrieval_encyclo"]
        st.session_state.encyclo_source_filter = preset["source_filter"]


def render_config_panel(config):
    """Affiche le panneau de configuration"""
    st.markdown("### ⚙️ Configuration")

    from core.utils import get_ollama_models
    raw_models = get_ollama_models()
    filtered_models = [m for m in raw_models if m not in _EXCLUDED]

    def _label(m):
        tag = _LABELS.get(m)
        return f"{m}  ({tag})" if tag else m

    current_model = st.session_state.get('current_model', config['model']['default'])
    default_index = filtered_models.index(current_model) if current_model in filtered_models else 0

    selected_model = st.selectbox(
        "Modèle",
        filtered_models,
        index=default_index,
        key="model_selector",
        format_func=_label,
        help="Modèles Ollama disponibles localement"
    )
    st.session_state.current_model = selected_model

    # Précharger le modèle en mémoire GPU dès la sélection
    if selected_model != st.session_state.get("_last_preloaded_model"):
        _preload_model_bg(selected_model)
        st.session_state._last_preloaded_model = selected_model
        st.toast(f"⏳ Chargement de **{selected_model}** en mémoire...", icon="🔄")

    st.markdown("---")

    # Mode
    mode = st.selectbox(
        "Mode",
        ["MJ immersif", "Encyclopédique"],
        index=0 if st.session_state.get("mode", "MJ immersif") == "MJ immersif" else 1,
        key="mode_selector"
    )
    st.session_state.mode = mode
    st.caption("MJ immersif = Réponse détaillée | Encyclopédique = Réponse factuelle")

    st.markdown("---")

    # Sliders
    col1, col2 = st.columns(2)

    with col1:
        if mode == "MJ immersif":
            st.session_state.setdefault('temp_slider', float(st.session_state.get('temperature', 0.8)))
            temp = st.slider(
                "Température",
                0.0, 1.0,
                key="temp_slider",
                step=0.05,
                help="0.0 = Factuel/fidèle au contexte | 1.0 = Créatif (hallucine plus)"
            )
            st.session_state.temperature = temp
            st.caption(f"Actuel: {temp}")
        else:
            st.caption("🔒 Température fixée à 0.0 en mode Encyclopédique")

    with col2:
        st.session_state.setdefault('top_p_slider', float(st.session_state.get('top_p', 0.95)))
        top_p = st.slider(
            "Top-p",
            0.0, 1.0,
            key="top_p_slider",
            step=0.05,
            help="Diversité du vocabulaire — 1.0 = tous les tokens possibles"
        )
        st.session_state.top_p = top_p
        st.caption(f"Actuel: {top_p}")

    # Taille du contexte (num_ctx)
    _ctx_default = config.get('model', {}).get('num_ctx', 32768)
    _ctx_options = [16384, 32768, 49152, 65536]
    _ctx_labels  = {16384: "16K", 32768: "32K", 49152: "48K", 65536: "64K"}
    st.session_state.setdefault('num_ctx_slider', st.session_state.get('num_ctx', _ctx_default))
    ctx_val = st.select_slider(
        "Contexte (num_ctx)",
        options=_ctx_options,
        format_func=lambda x: _ctx_labels[x],
        key="num_ctx_slider",
        help="Taille de la fenêtre de contexte du modèle. 32K = bon équilibre. 64K = plus lent, plus de VRAM."
    )
    st.session_state.num_ctx = ctx_val

    st.markdown("---")

    # Source filter pour mode encyclopédique
    if mode == "Encyclopédique":
        st.subheader("📚 Filtre des sources")

        _filter_options = [
            ("📖 Règles uniquement", "rules_only"),
            ("🌍 Univers + Romans", "universe_only"),
            ("📖🌍 Règles + Univers (sans romans)", "rules_and_universe"),
        ]
        _filter_index = next(
            (i for i, (_, v) in enumerate(_filter_options) if v == st.session_state.encyclo_source_filter),
            2
        )
        source_filter = st.selectbox(
            "Type de sources",
            _filter_options,
            index=_filter_index,
            key="source_filter_selector",
            format_func=lambda x: x[0]
        )
        st.session_state.encyclo_source_filter = source_filter[1]

        st.session_state.setdefault('k_retrieval_slider', st.session_state.get('encyclo_k_retrieval', 50))
        k_retrieval = st.slider(
            "Nombre de chunks (RAG)",
            1, 100,
            key="k_retrieval_slider",
            help="Chunks à récupérer du corpus (plus = plus de contexte, mais plus lent)"
        )
        st.session_state.encyclo_k_retrieval = k_retrieval

        col5, col6 = st.columns(2)
        with col5:
            show_sources = st.checkbox(
                "Afficher les sources",
                value=st.session_state.show_sources,
                key="show_sources_checkbox",
                help="Montre les documents source utilisés"
            )
            st.session_state.show_sources = show_sources

        with col6:
            show_debug = st.checkbox(
                "Mode debug",
                value=st.session_state.get('show_debug_chunks', False),
                key="show_debug_checkbox",
                help="Affiche le contexte complet envoyé au modèle (plus verbeux)"
            )
            st.session_state.show_debug_chunks = show_debug

    st.markdown("---")

    # Actions
    col7, col8 = st.columns(2)

    with col7:
        if st.button("💾 Sauvegarder la session"):
            from core.memory import SessionManager
            st.session_state.session_manager.save_session(
                session_name="manual_save",
                mj_memory=st.session_state.mj_memory,
                encyclo_memory=st.session_state.encyclo_memory,
                metadata={"manual_save": True}
            )
            st.success("✅ Session sauvegardée !")

    with col8:
        if st.button("🗑️ Tout effacer"):
            st.session_state.mj_memory.clear()
            st.session_state.encyclo_memory.clear()
            st.session_state.game_state = GameState()
            st.session_state.timeline.clear()
            if hasattr(st.session_state, 'statistics'):
                st.session_state.statistics = SessionManager(paths['save_dir'])
            st.rerun()

    st.markdown("---")

    # Déchargement du modèle GPU
    current_model = st.session_state.get('current_model', '')
    if st.button("🔌 Décharger le modèle", use_container_width=True,
                 help="Libère la VRAM en déchargeant le modèle actuel d'Ollama"):
        try:
            import urllib.request, json as _j
            payload = _j.dumps({"model": current_model, "keep_alive": 0}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            st.success(f"✅ `{current_model}` déchargé — VRAM libérée")
            st.session_state._last_preloaded_model = None
        except Exception as e:
            st.error(f"❌ Impossible de décharger : {e}")


def render_memory_display(mode: str):
    """Affiche la mémoire selon le mode"""
    from app_memory import render_memory_content

    render_memory_content(mode)


def render_character_viewer_old():
    """Affiche un lecteur de PDF (version alternative)"""
    st.markdown("### 📄 Lecteur de PDF (Fallback)")
    st.warning("Cette vue a été remplacée par la sidebar.")

    char_manager = st.session_state.char_manager
    selected = st.session_state.selected_character

    if not selected or selected not in [c.file_path for c in char_manager.characters]:
        st.info("Aucun personnage sélectionné.")
        return

    char = char_manager.get_character(selected)
    if char and char.is_pdf:
        try:
            import streamlit.components.v1 as components
            html_content = st.session_state.get('pdf_html', '')
            if html_content:
                components.html(html_content, height=850, scrolling=False)
        except Exception as e:
            st.error(f"Erreur d'affichage: {e}")
            st.info("Utilisez la sidebar pour afficher le PDF.")
    else:
        st.info("Lecture uniquement disponible pour les PDFs.")


def render_sources_display(result):
    """Affiche les sources de manière formatée"""
    with st.expander(f"📚 Sources ({len(result['sources'])} documents)", expanded=False):
        for i, doc in enumerate(result['sources'], 1):
            preview = doc.page_content[:400].replace("\n", " ")
            st.markdown(f"**Source {i}:** {preview}...")


def render_debug_chunks_display(result):
    """Affiche les chunks de debug"""
    if not st.session_state.get('show_debug_chunks', False):
        return

    # Afficher quel filtre est actif
    filter_names = {
        "rules_only": "📖 Règles uniquement",
        "universe_only": "🌍 Univers + Romans",
        "rules_and_universe": "📖🌍 Règles + Univers (sans romans)"
    }
    current_source_filter = st.session_state.get('encyclo_source_filter', 'rules_and_universe')
    active_filter = filter_names.get(current_source_filter, current_source_filter)

    with st.expander(f"🔍 DEBUG: Chunks récupérés ({len(result['sources'])} chunks)", expanded=False):
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