# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [2.0.0] - 2025-01-XX

### 🎉 Refonte majeure complète

Cette version représente une réécriture complète du projet avec des améliorations majeures en termes d'architecture, de performances et de fonctionnalités.

### ✨ Ajouté

#### Architecture
- **Modularisation complète** : Séparation en modules `core/` pour meilleure maintenabilité
- **Configuration YAML** : Centralisation de tous les paramètres dans `config.yaml`
- **System de cache intelligent** : Cache basé sur les paramètres pour éviter les reconstructions inutiles
- **Gestion d'erreurs robuste** : Try-catch appropriés et messages d'erreur informatifs

#### Fonctionnalités principales
- **Mode MJ Immersif amélioré**
  - Timeline interactive avec visualisation Plotly
  - Niveaux de narration multiples (court, détaillé, immersif)
  - Tracking automatique des PNJ, lieux, intrigues
  - Système d'icônes pour l'état du jeu
  
- **Mode Encyclopédique optimisé**
  - Mémoire courte contextuelle
  - Réponses factuelles précises
  - Historique des questions
  
- **Système de mémoire avancé**
  - Limitation intelligente de taille
  - Persistance automatique
  - Format pour injection dans prompts
  - Horodatage des échanges

- **Gestion de sessions**
  - Sauvegarde/chargement de parties complètes
  - Liste des sessions disponibles
  - Export en Markdown
  - Métadonnées de session
  - Auto-save configurable

- **Gestion de personnages**
  - Visualiseur de fiches amélioré
  - Support multi-formats (PDF, TXT, MD)
  - Recherche dans les fiches
  - Onglets pour organisation

#### RAG & IA
- **Parsing structuré robuste**
  - Extraction d'options avec patterns multiples
  - Extraction d'entités (PNJ, lieux, intrigues)
  - Nettoyage automatique du texte
  - Score de confiance RAG
  
- **Optimisations RAG**
  - Chunking configurable
  - K retrieval dynamique
  - Support CUDA pour embeddings
  - Fallback CPU automatique

#### UX/UI
- **Interface modernisée**
  - Layout deux colonnes optimisé
  - Sidebar organisée avec sections
  - Statistiques de session
  - Indicateurs visuels de statut
  - CSS personnalisé avec thème cardinal
  
- **Réglages experts**
  - Température et top-p ajustables
  - K retrieval variable
  - Affichage des sources optionnel

#### DevOps
- **Docker support** : Dockerfile et docker-compose
- **Tests unitaires** : Suite complète avec pytest
- **Scripts de démarrage** : Bash (Linux/Mac) et Batch (Windows)
- **Setup automatisé** : Script d'installation interactif
- **CI/CD ready** : Structure prête pour GitHub Actions

### 🔧 Modifié

#### Améliorations techniques
- **Gestion du context** : Correction du passage de context au prompt (bug majeur v1)
- **Cache du QA chain** : Recréation intelligente basée sur les paramètres
- **Gestion des modèles Ollama** : Détection dynamique avec fallback
- **Imports** : Priorisation de langchain-ollama sur community

#### Performance
- **Chargement optimisé** : Cache des documents et vectorstore
- **Mémoire limitée** : Évite l'explosion de la mémoire en sessions longues
- **Lazy loading** : Embeddings chargés à la demande

#### UX
- **Messages d'erreur clairs** : Plus informatifs et actionnables
- **Feedback utilisateur** : Spinners et indicateurs de progression
- **Healthchecks** : Vérifications au démarrage

### 🐛 Corrigé

#### Bugs critiques v1
- ❌ Context passé deux fois au prompt (full_text + RAG context)
- ❌ QA chain non recréé lors du changement de modèle
- ❌ Vectordb reconstruit à chaque changement de K
- ❌ Mémoire non limitée → explosion du contexte
- ❌ Parsing regex fragile
- ❌ Pas de validation des chemins (hardcodé Windows)
- ❌ Exceptions trop génériques

#### Autres corrections
- Import errors avec différentes versions de LangChain
- Problèmes d'encodage avec certains PDFs
- Crash lors de la lecture de fiches corrompues
- Timeline non mise à jour correctement
- État du jeu non persisté entre sessions

### 🗑️ Supprimé

- Dépendance à des chemins hardcodés Windows
- Code dupliqué dans plusieurs fonctions
- Variables globales inutiles
- Imports inutilisés

### 📚 Documentation

- **README complet** avec guide d'installation détaillé
- **CONTRIBUTING.md** pour les contributeurs
- **Docstrings** pour toutes les fonctions publiques
- **Type hints** sur les fonctions principales
- **Commentaires explicatifs** dans le code complexe

### 🔒 Sécurité

- Utilisation d'utilisateur non-root dans Docker
- Validation des chemins de fichiers
- Pas de secrets hardcodés
- .gitignore complet pour éviter les fuites

---

## [1.0.0] - 2024-XX-XX

### Ajouté
- Version initiale du projet
- Mode MJ basique
- Mode Encyclopédique basique
- Support RAG avec Chroma
- Lecture de PDFs
- Affichage fiches personnages
- Intégration Ollama

### Problèmes connus
- Context dupliqué dans les prompts
- Cache QA chain non invalidé
- Mémoire non limitée
- Parsing fragile
- Chemins hardcodés

---

## Format des versions

- **MAJOR** : Changements incompatibles avec les versions précédentes
- **MINOR** : Ajout de fonctionnalités rétro-compatibles
- **PATCH** : Corrections de bugs rétro-compatibles

## Liens
- [2.0.0] : Version actuelle (refonte complète)
- [1.0.0] : Version originale