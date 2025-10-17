#!/bin/bash
# start.sh - Script de démarrage rapide pour Assistant MJ

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Vérifier si Python est installé
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION détecté"
        return 0
    else
        print_error "Python 3 n'est pas installé"
        return 1
    fi
}

# Vérifier si l'environnement virtuel existe
check_venv() {
    if [ -d "venv" ]; then
        print_success "Environnement virtuel trouvé"
        return 0
    else
        print_warning "Environnement virtuel non trouvé"
        return 1
    fi
}

# Créer l'environnement virtuel
create_venv() {
    print_info "Création de l'environnement virtuel..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        print_success "Environnement virtuel créé"
        return 0
    else
        print_error "Échec de la création de l'environnement virtuel"
        return 1
    fi
}

# Activer l'environnement virtuel
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Environnement virtuel activé"
        return 0
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
        print_success "Environnement virtuel activé"
        return 0
    else
        print_error "Impossible d'activer l'environnement virtuel"
        return 1
    fi
}

# Installer les dépendances
install_deps() {
    if [ -f "requirements.txt" ]; then
        print_info "Installation des dépendances..."
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
        if [ $? -eq 0 ]; then
            print_success "Dépendances installées"
            return 0
        else
            print_error "Échec de l'installation des dépendances"
            return 1
        fi
    else
        print_error "Fichier requirements.txt non trouvé"
        return 1
    fi
}

# Vérifier Ollama
check_ollama() {
    if command -v ollama &> /dev/null; then
        print_success "Ollama est installé"
        
        # Vérifier si Ollama est en cours d'exécution
        if pgrep -x "ollama" > /dev/null; then
            print_success "Ollama est en cours d'exécution"
        else
            print_warning "Ollama n'est pas en cours d'exécution"
            print_info "Démarre Ollama avec: ollama serve"
        fi
        
        return 0
    else
        print_warning "Ollama n'est pas installé"
        print_info "Installe depuis: https://ollama.ai"
        return 1
    fi
}

# Vérifier le fichier de config
check_config() {
    if [ -f "config.yaml" ]; then
        print_success "Fichier config.yaml trouvé"
        return 0
    else
        print_warning "Fichier config.yaml non trouvé"
        print_info "Exécute: python setup.py"
        return 1
    fi
}

# Vérifier la structure de répertoires
check_directories() {
    CONFIG_BASE_DIR=$(grep "base_dir:" config.yaml 2>/dev/null | cut -d'"' -f2)
    
    if [ -z "$CONFIG_BASE_DIR" ]; then
        print_warning "Impossible de lire le répertoire de base depuis config.yaml"
        return 1
    fi
    
    # Expand ~ si présent
    CONFIG_BASE_DIR="${CONFIG_BASE_DIR/#\~/$HOME}"
    
    if [ -d "$CONFIG_BASE_DIR" ]; then
        print_success "Répertoire de base trouvé: $CONFIG_BASE_DIR"
        return 0
    else
        print_warning "Répertoire de base non trouvé: $CONFIG_BASE_DIR"
        print_info "Exécute: python setup.py"
        return 1
    fi
}

# Démarrer l'application
start_app() {
    print_info "Démarrage de l'application..."
    echo ""
    streamlit run app.py
}

# Fonction d'aide
show_help() {
    echo "Usage: ./start.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --setup      Exécute la configuration initiale"
    echo "  --install    Installe uniquement les dépendances"
    echo "  --check      Vérifie l'installation sans démarrer"
    echo "  --help       Affiche cette aide"
    echo ""
}

# Programme principal
main() {
    print_header "🗡️  Assistant MJ - Les Lames du Cardinal"
    
    # Gérer les arguments
    case "$1" in
        --setup)
            python3 setup.py
            exit $?
            ;;
        --install)
            check_python || exit 1
            if ! check_venv; then
                create_venv || exit 1
            fi
            activate_venv || exit 1
            install_deps || exit 1
            print_success "Installation terminée"
            exit 0
            ;;
        --check)
            check_python || exit 1
            check_venv || print_warning "Environnement virtuel manquant"
            check_ollama
            check_config || print_warning "Configuration manquante"
            check_directories
            exit 0
            ;;
        --help)
            show_help
            exit 0
            ;;
    esac
    
    # Vérifications
    print_header "Vérifications"
    
    check_python || exit 1
    
    if ! check_venv; then
        read -p "Créer l'environnement virtuel? (O/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            create_venv || exit 1
        else
            exit 1
        fi
    fi
    
    activate_venv || exit 1
    
    # Vérifier si les dépendances sont installées
    if ! python -c "import streamlit" &> /dev/null; then
        print_warning "Dépendances non installées"
        read -p "Installer les dépendances? (O/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            install_deps || exit 1
        else
            exit 1
        fi
    else
        print_success "Dépendances installées"
    fi
    
    check_ollama
    check_config || print_warning "Exécute python setup.py pour créer la config"
    check_directories
    
    # Démarrer
    print_header "Démarrage"
    start_app
}

# Rendre le script exécutable: chmod +x start.sh
main "$@"