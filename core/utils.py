"""
core/utils.py
Fonctions utilitaires diverses
"""

import subprocess
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional


def load_config(config_path: Path) -> Dict[str, Any]:
    """Charge la configuration depuis un fichier YAML"""
    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration non trouvé: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Expand paths
    base_dir = Path(config['paths']['base_dir']).expanduser()
    config['paths']['base_dir'] = base_dir
    
    # Convertir les chemins relatifs en absolus
    for key in ['pdf_root', 'char_dir', 'db_dir', 'save_dir', 'memory_dir']:
        if key in config['paths']:
            path = config['paths'][key]
            if not Path(path).is_absolute():
                config['paths'][key] = base_dir / path
            else:
                config['paths'][key] = Path(path)
    
    return config


def get_ollama_models() -> List[str]:
    """Récupère la liste des modèles Ollama disponibles"""
    try:
        output = subprocess.check_output(
            ["ollama", "list"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5
        )
        
        models = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.lower().startswith("name") or line.startswith("---"):
                continue
            
            # Premier token = nom du modèle
            parts = line.split()
            if parts:
                candidate = parts[0]
                # Validation basique
                if re.match(r"^[\w\-\.:]+$", candidate):
                    models.append(candidate)
        
        return models if models else get_fallback_models()
    
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return get_fallback_models()


def get_fallback_models() -> List[str]:
    """Retourne une liste de modèles par défaut"""
    return [
        "mistral-nemo",
        "llama3",
        "llama3:70b",
        "mistral",
        "phi3",
        "qwen2.5"
    ]


def validate_ollama_installation() -> bool:
    """Vérifie si Ollama est installé et accessible"""
    try:
        subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            timeout=3,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def format_file_size(size_bytes: int) -> str:
    """Formate une taille de fichier en unités lisibles"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Tronque un texte intelligemment"""
    if len(text) <= max_length:
        return text
    
    # Tronque au dernier espace avant max_length
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return truncated + suffix


def create_directory_structure(base_dir: Path, subdirs: List[str]):
    """Crée une structure de répertoires"""
    base_dir.mkdir(parents=True, exist_ok=True)
    for subdir in subdirs:
        (base_dir / subdir).mkdir(parents=True, exist_ok=True)


def export_session_to_markdown(
    mj_memory: List[Dict[str, str]],
    game_state: Dict[str, Any],
    session_name: str,
    output_path: Path
) -> bool:
    """Exporte une session en format Markdown"""
    try:
        lines = [
            f"# Session: {session_name}",
            "",
            "## État du jeu",
            ""
        ]
        
        # État PNJ
        if game_state.get("npcs"):
            lines.append("### PNJ")
            for name, status in game_state["npcs"].items():
                lines.append(f"- **{name}**: {status}")
            lines.append("")
        
        # État Lieux
        if game_state.get("locations"):
            lines.append("### Lieux")
            for name, status in game_state["locations"].items():
                lines.append(f"- **{name}**: {status}")
            lines.append("")
        
        # État Intrigues
        if game_state.get("intrigues"):
            lines.append("### Intrigues")
            for name, status in game_state["intrigues"].items():
                lines.append(f"- **{name}**: {status}")
            lines.append("")
        
        # Historique des échanges
        lines.append("## Historique")
        lines.append("")
        
        for i, entry in enumerate(mj_memory, 1):
            lines.append(f"### Tour {i}")
            lines.append("")
            lines.append(f"**Joueur:** {entry['user']}")
            lines.append("")
            lines.append(f"**MJ:** {entry['assistant']}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return True
    
    except Exception as e:
        print(f"Erreur export Markdown: {e}")
        return False


class ColorScheme:
    """Schéma de couleurs pour l'interface"""
    
    PRIMARY = "#8B0000"  # Rouge cardinal
    SECONDARY = "#DAA520"  # Or
    SUCCESS = "#228B22"
    WARNING = "#FF8C00"
    DANGER = "#DC143C"
    INFO = "#4682B4"
    
    @classmethod
    def get_css(cls) -> str:
        """Retourne le CSS personnalisé"""
        return f"""
        <style>
        .stButton>button {{
            background-color: {cls.PRIMARY};
            color: white;
        }}
        .stButton>button:hover {{
            background-color: {cls.DANGER};
        }}
        </style>
        """