#!/bin/bash
# deploy_to_github.sh - Script de déploiement automatique sur GitHub

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Déploiement GitHub${NC}"
echo -e "${BLUE}  Assistant MJ - Les Lames du Cardinal${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Vérifier si git est installé
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git n'est pas installé${NC}"
    echo "Installe Git depuis: https://git-scm.com/downloads"
    exit 1
fi

echo -e "${GREEN}✓${NC} Git détecté\n"

# Demander l'URL du repository
read -p "URL de ton repository GitHub (ex: https://github.com/username/lames-mj.git): " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo -e "${RED}❌ URL du repository requise${NC}"
    exit 1
fi

# Vérifier si c'est déjà un repository git
if [ -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Repository Git existant détecté${NC}"
    read -p "Voulez-vous le réinitialiser? (o/N): " REINIT
    
    if [[ $REINIT =~ ^[Oo]$ ]]; then
        rm -rf .git
        echo -e "${GREEN}✓${NC} Repository réinitialisé"
    fi
fi

# Initialiser le repository si nécessaire
if [ ! -d ".git" ]; then
    echo -e "${BLUE}📦 Initialisation du repository Git...${NC}"
    git init
    echo -e "${GREEN}✓${NC} Repository initialisé\n"
fi

# Configurer le remote
echo -e "${BLUE}🔗 Configuration du remote...${NC}"
if git remote | grep -q "origin"; then
    git remote remove origin
fi
git remote add origin "$REPO_URL"
echo -e "${GREEN}✓${NC} Remote configuré\n"

# Vérifier les identifiants Git
echo -e "${BLUE}👤 Vérification des identifiants Git...${NC}"
GIT_NAME=$(git config user.name)
GIT_EMAIL=$(git config user.email)

if [ -z "$GIT_NAME" ]; then
    read -p "Nom d'utilisateur Git: " GIT_NAME
    git config user.name "$GIT_NAME"
fi

if [ -z "$GIT_EMAIL" ]; then
    read -p "Email Git: " GIT_EMAIL
    git config user.email "$GIT_EMAIL"
fi

echo -e "${GREEN}✓${NC} Identifiants: $GIT_NAME <$GIT_EMAIL>\n"

# Créer .gitignore si inexistant
if [ ! -f ".gitignore" ]; then
    echo -e "${BLUE}📝 Création de .gitignore...${NC}"
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# Data
**/Data/**
!**/Data/README.txt
**/Characters/**
!**/Characters/README.txt
**/lames_db/**
**/saved_sessions/**
**/memory/**

# Logs
*.log

# Config local
config.local.yaml

# OS
Thumbs.db
EOF
    echo -e "${GREEN}✓${NC} .gitignore créé\n"
fi

# Créer un README si inexistant (minimal)
if [ ! -f "README.md" ]; then
    echo -e "${BLUE}📝 Création de README.md basique...${NC}"
    echo "# Assistant MJ - Les Lames du Cardinal" > README.md
    echo -e "${GREEN}✓${NC} README.md créé\n"
fi

# Afficher les fichiers à commiter
echo -e "${BLUE}📋 Fichiers à ajouter:${NC}"
git status --short
echo ""

# Confirmer avant de continuer
read -p "Continuer avec le commit et push? (O/n): " CONFIRM
if [[ $CONFIRM =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}⏭️  Opération annulée${NC}"
    exit 0
fi

# Ajouter tous les fichiers
echo -e "${BLUE}➕ Ajout des fichiers...${NC}"
git add .
echo -e "${GREEN}✓${NC} Fichiers ajoutés\n"

# Demander le message de commit
read -p "Message de commit [Refonte complète v2.0 - Architecture modulaire]: " COMMIT_MSG
COMMIT_MSG=${COMMIT_MSG:-"Refonte complète v2.0 - Architecture modulaire"}

# Commit
echo -e "${BLUE}💾 Commit des changements...${NC}"
git commit -m "$COMMIT_MSG"
echo -e "${GREEN}✓${NC} Commit effectué\n"

# Demander la branche
read -p "Nom de la branche [main]: " BRANCH
BRANCH=${BRANCH:-main}

# Renommer la branche si nécessaire
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    git branch -M "$BRANCH"
    echo -e "${GREEN}✓${NC} Branche renommée en $BRANCH\n"
fi

# Push
echo -e "${BLUE}🚀 Push vers GitHub...${NC}"
echo -e "${YELLOW}Note: Tu devras peut-être entrer tes identifiants GitHub${NC}\n"

if git push -u origin "$BRANCH"; then
    echo -e "\n${GREEN}✅ Succès!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ Code poussé sur GitHub${NC}"
    echo -e "${GREEN}✓ Repository: $REPO_URL${NC}"
    echo -e "${GREEN}✓ Branche: $BRANCH${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    # Proposer d'ouvrir le repo dans le navigateur
    read -p "Ouvrir le repository dans le navigateur? (o/N): " OPEN_BROWSER
    if [[ $OPEN_BROWSER =~ ^[Oo]$ ]]; then
        # Extraire l'URL web depuis l'URL git
        WEB_URL=$(echo "$REPO_URL" | sed 's/\.git$//')
        if command -v xdg-open &> /dev/null; then
            xdg-open "$WEB_URL"
        elif command -v open &> /dev/null; then
            open "$WEB_URL"
        else
            echo "Ouvre ce lien: $WEB_URL"
        fi
    fi
else
    echo -e "\n${RED}❌ Erreur lors du push${NC}"
    echo -e "${YELLOW}Causes possibles:${NC}"
    echo "  - Identifiants incorrects"
    echo "  - Repository n'existe pas sur GitHub"
    echo "  - Pas les droits en écriture"
    echo "  - Problème de connexion"
    echo ""
    echo -e "${BLUE}Solutions:${NC}"
    echo "  1. Crée le repository sur GitHub d'abord"
    echo "  2. Vérifie tes identifiants Git"
    echo "  3. Utilise un token d'accès personnel (PAT) au lieu du mot de passe"
    echo "     https://github.com/settings/tokens"
    exit 1
fi

# Proposer de créer un tag de version
read -p "Créer un tag de version v2.0.0? (o/N): " CREATE_TAG
if [[ $CREATE_TAG =~ ^[Oo]$ ]]; then
    git tag -a v2.0.0 -m "Version 2.0.0 - Refonte complète"
    git push origin v2.0.0
    echo -e "${GREEN}✓${NC} Tag v2.0.0 créé et poussé"
fi

echo -e "\n${GREEN}🎉 Déploiement terminé!${NC}\n"