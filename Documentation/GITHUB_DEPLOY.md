# 🚀 Guide de déploiement GitHub

Trois méthodes pour pousser ton code sur GitHub.

## 📋 Prérequis

1. **Git installé** : `git --version`
   - Si non installé : https://git-scm.com/downloads

2. **Compte GitHub** : https://github.com/join

3. **Repository créé sur GitHub**
   - Va sur https://github.com/new
   - Nom suggéré : `lames-cardinal-mj` ou `assistant-mj-lames`
   - **Ne pas initialiser avec README** (on a déjà les fichiers)
   - Note l'URL : `https://github.com/TON_USERNAME/TON_REPO.git`

---

## 🎯 Méthode 1 : Script automatique (RECOMMANDÉ)

### Linux / Mac

```bash
# Rendre le script exécutable
chmod +x deploy_to_github.sh

# Lancer le script
./deploy_to_github.sh
```

### Windows

```batch
REM Double-cliquer sur deploy_to_github.bat
REM ou dans le terminal :
deploy_to_github.bat
```

Le script te guidera étape par étape ! 🎉

---

## 🔧 Méthode 2 : Commandes manuelles

### Étape 1 : Créer le repository sur GitHub

1. Va sur https://github.com/new
2. Nom : `lames-cardinal-mj`
3. Description : "Assistant MJ pour Les Lames du Cardinal avec RAG et Ollama"
4. **Public** ou **Private** (ton choix)
5. **NE PAS** cocher "Initialize with README"
6. Clique sur "Create repository"
7. **Note l'URL** affichée (format: `https://github.com/username/repo.git`)

### Étape 2 : Initialiser Git localement

Ouvre un terminal dans ton dossier projet et exécute :

```bash
# Initialiser le repository
git init

# Configurer tes identifiants (si pas déjà fait)
git config user.name "Ton Nom"
git config user.email "ton@email.com"

# Vérifier que .gitignore existe (sinon copie le contenu ci-dessous)
cat .gitignore
```

### Étape 3 : Ajouter les fichiers

```bash
# Voir les fichiers à ajouter
git status

# Ajouter tous les fichiers
git add .

# Vérifier ce qui sera commité
git status
```

### Étape 4 : Faire le commit

```bash
# Commit avec un message descriptif
git commit -m "feat: refonte complète v2.0 - architecture modulaire

- Modularisation complète (core/)
- Configuration YAML
- Système de mémoire avec limite
- Sessions sauvegardables
- Export Markdown
- Timeline interactive
- Tests unitaires
- Documentation complète
- Scripts de démarrage
- Support Docker"
```

### Étape 5 : Connecter au repository GitHub

```bash
# Remplace par TON URL GitHub
git remote add origin https://github.com/TON_USERNAME/TON_REPO.git

# Vérifier
git remote -v
```

### Étape 6 : Renommer la branche (si nécessaire)

```bash
# La plupart des repos utilisent 'main' maintenant
git branch -M main
```

### Étape 7 : Pousser sur GitHub

```bash
# Push initial
git push -u origin main
```

**Note** : Tu devras entrer tes identifiants GitHub.

### Étape 8 : Créer un tag de version (optionnel)

```bash
# Créer un tag
git tag -a v2.0.0 -m "Version 2.0.0 - Refonte complète"

# Pousser le tag
git push origin v2.0.0
```

---

## 🔐 Méthode 3 : Avec token d'accès (plus sécurisé)

### Créer un Personal Access Token (PAT)

1. Va sur https://github.com/settings/tokens
2. Clique "Generate new token" → "Generate new token (classic)"
3. Nom : `lames-mj-deploy`
4. Expire : 90 jours (ou plus)
5. Scopes : Coche **`repo`** (full control)
6. Clique "Generate token"
7. **COPIE LE TOKEN** (tu ne le reverras plus !)

### Utiliser le token

Au lieu de ton mot de passe, utilise le token :

```bash
# Format de l'URL avec token
git remote add origin https://TOKEN@github.com/USERNAME/REPO.git

# Exemple :
# git remote add origin https://ghp_abcd1234xyz@github.com/johndoe/lames-mj.git

# Puis push normalement
git push -u origin main
```

Ou lors du push, quand on te demande le mot de passe, colle ton **token**.

---

## ❓ Résolution de problèmes

### Erreur : "remote origin already exists"

```bash
# Supprimer le remote existant
git remote remove origin

# Puis recommencer
git remote add origin https://github.com/USERNAME/REPO.git
```

### Erreur : "Authentication failed"

**Causes** :
1. Mauvais identifiants
2. Depuis août 2021, GitHub refuse les mots de passe

**Solutions** :
- Utilise un **Personal Access Token** (voir Méthode 3)
- Ou configure SSH : https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### Erreur : "Repository not found"

1. Vérifie que le repo existe sur GitHub
2. Vérifie l'URL (copie-colle depuis GitHub)
3. Vérifie que tu as les droits d'accès

### Erreur : "failed to push some refs"

```bash
# Si le repo GitHub a des fichiers que tu n'as pas localement
git pull origin main --rebase

# Puis push
git push -u origin main
```

### Les fichiers sensibles sont commités

```bash
# Supprimer du cache Git
git rm --cached fichier_sensible.txt

# Ajouter au .gitignore
echo "fichier_sensible.txt" >> .gitignore

# Commit et push
git commit -m "fix: retrait fichier sensible"
git push
```

---

## 📝 Contenu du .gitignore

Vérifie que ton `.gitignore` contient bien :

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
env/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# Data (IMPORTANT!)
**/Data/**
!**/Data/README.txt
**/Characters/**
!**/Characters/README.txt
**/lames_db/**
**/saved_sessions/**
**/memory/**

# Logs
*.log
logs/

# Config local
config.local.yaml

# OS
Thumbs.db
```

---

## 🎨 Personnaliser ton README GitHub

Une fois poussé, édite le README.md sur GitHub pour ajouter :

### Badges

```markdown
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
```

### Screenshot

Ajoute une capture d'écran de l'interface !

### Liens rapides

```markdown
## 🔗 Liens rapides

- [📚 Documentation](./README.md)
- [🎯 Exemples](./EXAMPLES.md)
- [🤝 Contribuer](./CONTRIBUTING.md)
- [📝 Changelog](./CHANGELOG.md)
```

---

## 🔄 Mises à jour futures

Pour pousser des modifications ultérieures :

```bash
# 1. Voir les changements
git status

# 2. Ajouter les fichiers modifiés
git add .

# 3. Commit
git commit -m "fix: correction du bug X"

# 4. Push
git push
```

---

## 🌟 Commandes Git utiles

```bash
# Voir l'historique
git log --oneline --graph

# Voir les différences avant commit
git diff

# Annuler le dernier commit (garde les fichiers)
git reset --soft HEAD~1

# Voir les branches
git branch -a

# Créer une branche de développement
git checkout -b develop

# Revenir à main
git checkout main

# Fusionner develop dans main
git merge develop

# Cloner ton repo ailleurs
git clone https://github.com/USERNAME/REPO.git
```

---

## 📞 Besoin d'aide ?

- Documentation Git : https://git-scm.com/doc
- GitHub Guides : https://guides.github.com/
- Problèmes d'authentification : https://docs.github.com/en/authentication

---

## ✅ Checklist finale

Avant de pousser, vérifie :

- [ ] `.gitignore` est présent et complet
- [ ] Pas de mots de passe ou tokens dans le code
- [ ] Pas de fichiers de données sensibles (Data/, Characters/)
- [ ] README.md est à jour
- [ ] Les tests passent (`pytest`)
- [ ] config.yaml ne contient pas de chemins absolus personnels

---

Bon déploiement ! 🚀

Si tu as des questions, ouvre une issue sur GitHub.