"""
setup.py
Script d'installation et de configuration initiale
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil


def print_header(text):
    """Affiche un header stylisé"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


def check_python_version():
    """Vérifie la version de Python"""
    print("🔍 Vérification de Python...")
    
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ requis!")
        print(f"   Version actuelle: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} détecté")
    return True


def check_ollama():
    """Vérifie si Ollama est installé"""
    print("\n🔍 Vérification d'Ollama...")
    
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Ollama installé")
            
            # Lister les modèles
            try:
                models_result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if models_result.returncode == 0:
                    lines = models_result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        print(f"   Modèles disponibles: {len(lines)-1}")
                    else:
                        print("⚠️  Aucun modèle téléchargé")
                        print("   Exécute: ollama pull mistral-nemo")
            except Exception:
                pass
            
            return True
        else:
            print("❌ Ollama non installé ou non accessible")
            print("   Télécharge depuis: https://ollama.ai")
            return False
    
    except FileNotFoundError:
        print("❌ Ollama non installé")
        print("   Télécharge depuis: https://ollama.ai")
        return False
    
    except Exception as e:
        print(f"⚠️  Erreur lors de la vérification: {e}")
        return False


def create_directory_structure(base_dir):
    """Crée la structure de répertoires"""
    print("\n📁 Création de la structure de répertoires...")
    
    base_path = Path(base_dir).expanduser()
    
    dirs = [
        base_path,
        base_path / "Data",
        base_path / "Characters",
        base_path / "lames_db",
        base_path / "saved_sessions",
        base_path / "memory"
    ]
    
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    # Créer des fichiers README dans les dossiers importants
    readme_data = base_path / "Data" / "README.txt"
    if not readme_data.exists():
        readme_data.write_text(
            "Dépose ici tes PDFs et documents de règles du jeu.\n"
            "Formats supportés: .pdf, .txt, .md\n"
        )
    
    readme_chars = base_path / "Characters" / "README.txt"
    if not readme_chars.exists():
        readme_chars.write_text(
            "Dépose ici les fiches de personnages.\n"
            "Formats supportés: .pdf, .txt, .md\n"
        )
    
    return base_path


def create_config_file(base_dir):
    """Crée le fichier de configuration"""
    print("\n⚙️  Création du fichier config.yaml...")
    
    config_path = Path("config.yaml")
    
    if config_path.exists():
        response = input("   config.yaml existe déjà. Écraser? (o/N): ")
        if response.lower() != 'o':
            print("   ⏭️  Conservation du fichier existant")
            return
    
    config_content = f"""# Configuration - Assistant MJ Les Lames du Cardinal

# Chemins (utilise ~ pour home directory, ou chemins absolus)
paths:
  base_dir: "{base_dir}"
  pdf_root: "Data"
  char_dir: "Characters"
  db_dir: "lames_db"
  save_dir: "saved_sessions"
  memory_dir: "memory"

# Configuration du modèle
model:
  default: "mistral-nemo"
  temperature: 0.0
  top_p: 1.0
  fallback_models:
    - "llama3"
    - "mistral"
    - "phi3"

# Configuration RAG
rag:
  embedding_model: "all-MiniLM-L6-v2"
  k_retrieval: 6
  chunk_size: 1000
  chunk_overlap: 150
  use_cuda: true

# Configuration de la mémoire
memory:
  max_mj_memory: 30
  max_encyclo_memory: 10
  short_memory_context: 3

# Configuration UI
ui:
  default_mode: "MJ immersif"
  show_sources_default: false
  timeline_enabled: true
  auto_save_interval: 5

# Prompts
prompts:
  mj_system: |
    Tu es le Maître de Jeu des Lames du Cardinal.
    Tu dois répondre **uniquement** à partir des extraits fournis ci-dessous.
    Si l'information n'existe pas dans le contexte, réponds exactement : "Aucune information trouvée dans le corpus."
    N'invente JAMAIS d'informations.
    
  encyclo_system: |
    Tu es une encyclopédie du jeu 'Les Lames du Cardinal'.
    Réponds uniquement selon le contenu des extraits fournis.
    Si aucune information n'est trouvée, réponds exactement : "Aucune information trouvée dans le corpus."
    Ne crée jamais d'informations de toutes pièces.

# Options avancées
advanced:
  max_pdf_pages: 500
  enable_statistics: true
  export_format: "markdown"
"""
    
    config_path.write_text(config_content)
    print(f"   ✅ config.yaml créé")


def install_dependencies():
    """Installe les dépendances"""
    print("\n📦 Installation des dépendances...")
    
    requirements_path = Path("requirements.txt")
    
    if not requirements_path.exists():
        print("   ❌ requirements.txt non trouvé!")
        return False
    
    print("   Cela peut prendre quelques minutes...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("   ✅ Dépendances installées")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erreur lors de l'installation: {e}")
        return False


def download_ollama_model(model_name="mistral-nemo"):
    """Propose de télécharger un modèle Ollama"""
    print(f"\n🤖 Téléchargement du modèle {model_name}...")
    
    response = input(f"   Télécharger {model_name}? (o/N): ")
    
    if response.lower() != 'o':
        print("   ⏭️  Téléchargement annulé")
        return False
    
    try:
        print(f"   Téléchargement en cours (cela peut prendre plusieurs minutes)...")
        subprocess.run(
            ["ollama", "pull", model_name],
            check=True
        )
        print(f"   ✅ Modèle {model_name} téléchargé")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erreur lors du téléchargement: {e}")
        return False
    
    except FileNotFoundError:
        print("   ❌ Ollama non trouvé")
        return False


def main():
    """Fonction principale"""
    print_header("🗡️  INSTALLATION - ASSISTANT MJ LES LAMES DU CARDINAL")
    
    # Vérifications
    if not check_python_version():
        return
    
    has_ollama = check_ollama()
    
    # Demander le répertoire de base
    print("\n📂 Configuration du répertoire de base")
    default_dir = str(Path.home() / "LamesMJ")
    base_dir = input(f"   Répertoire de base [{default_dir}]: ").strip()
    
    if not base_dir:
        base_dir = default_dir
    
    # Créer la structure
    base_path = create_directory_structure(base_dir)
    
    # Créer le fichier de config
    create_config_file(base_dir)
    
    # Installer les dépendances
    print("\n📦 Installation des dépendances")
    install_deps = input("   Installer les dépendances Python? (O/n): ").strip()
    
    if install_deps.lower() != 'n':
        install_dependencies()
    
    # Télécharger un modèle Ollama
    if has_ollama:
        download_ollama_model("mistral-nemo")
    
    # Résumé
    print_header("✅ INSTALLATION TERMINÉE")
    
    print("📋 Prochaines étapes:")
    print(f"   1. Ajoute tes PDFs de règles dans: {base_path / 'Data'}")
    print(f"   2. Ajoute tes fiches de personnages dans: {base_path / 'Characters'}")
    print("   3. Lance l'application avec: streamlit run app.py")
    
    if not has_ollama:
        print("\n⚠️  N'oublie pas d'installer Ollama: https://ollama.ai")
    
    print("\n🎮 Bon jeu! 🗡️")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Installation annulée")
    except Exception as e:
        print(f"\n\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()