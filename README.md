# 🗡️ Assistant MJ - Les Lames du Cardinal

Assistant intelligent pour Maître de Jeu utilisant RAG (Retrieval-Augmented Generation) avec Ollama pour le jeu de rôle "Les Lames du Cardinal".

## ✨ Fonctionnalités

- **Mode MJ Immersif** : Narration interactive avec gestion de l'état du jeu (PNJ, lieux, intrigues)
- **Mode Encyclopédique** : Consultation factuelle des règles du jeu
- **RAG Avancé** : Recherche sémantique dans le corpus de règles avec Chroma
- **Mémoire Contextuelle** : Suivi des échanges avec limite intelligente
- **Timeline Interactive** : Visualisation de la progression de la partie
- **Gestion de Personnages** : Affichage des fiches de personnages
- **Sessions Sauvegardables** : Sauvegarde et chargement de parties
- **Export Markdown** : Génération de rapports de session
- **Multi-Modèles** : Changement de modèle Ollama à la volée
- **Statistiques** : Suivi des performances de session

## 📋 Prérequis

1. **Python 3.9+**
2. **Ollama** installé et en cours d'exécution
   - Installation : https://ollama.ai
   - Télécharger au moins un modèle : `ollama pull mistral-nemo`
3. **Poppler** (pour l'affichage PDF dans la sidebar)
   - Windows : Télécharger depuis https://github.com/oschwartz10612/poppler-windows/releases
   - Linux : `sudo apt-get install poppler-utils`
   - macOS : `brew install poppler`

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone <votre-repo>
cd lames-cardinal-mj
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Installer et configurer Poppler (Windows uniquement)

**Sur Windows**, Poppler doit être installé manuellement :

1. **Télécharger** : https://github.com/oschwartz10612/poppler-windows/releases/latest
2. **Extraire** dans un dossier (ex: `C:\poppler` ou `D:\IA\poppler-XX.XX.X`)
3. **Configurer le chemin** dans `app.py` (ligne 251) :
   ```python
   poppler_path = r"D:\IA\poppler-25.07.0\Library\bin"
   ```

**Sur Linux/macOS**, Poppler s'installe via le gestionnaire de paquets :
```bash
# Linux
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

### 5. Installer PyTorch (optionnel, pour GPU)

Pour accélérer les embeddings avec GPU :

```bash
# RTX 5090/5080/5070 Ti (architecture Blackwell) - Nécessite CUDA 12.8
pip install torch --index-url https://download.pytorch.org/whl/cu128

# RTX 4090/4080/3090 (CUDA 12.6)
pip install torch --index-url https://download.pytorch.org/whl/cu126

# RTX 3080/3070 (CUDA 11.8)
pip install torch --index-url https://download.pytorch.org/whl/cu118

# CPU uniquement
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Note RTX 50xx** : Ces GPUs (Blackwell sm_120) nécessitent PyTorch 2.7+ avec CUDA 12.8. Voir `INSTALLER_PYTORCH_CUDA.md` pour les détails.

### 6. Structure des dossiers

Créer la structure suivante (ou laisser l'app la créer automatiquement) :

```
~/LamesMJ/                  # Ou modifier dans config.yaml
├── Data/                   # PDFs et documents de règles
├── Characters/             # Fiches de personnages (.txt, .md, .pdf)
├── lames_db/              # Base vectorielle Chroma (auto-généré)
├── saved_sessions/        # Sessions sauvegardées
└── memory/                # Mémoire persistante
```

### 7. Configuration

Éditer `config.yaml` selon vos besoins :

```yaml
paths:
  base_dir: "~/LamesMJ"  # Modifier si nécessaire

model:
  default: "mistral-nemo"  # Votre modèle préféré

# ... autres paramètres
```

## 🎮 Utilisation

### Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvre dans votre navigateur par défaut.

### Premier lancement

1. **Ajouter les PDFs de règles** dans le dossier `Data/`
2. **Ajouter les fiches de personnages** dans `Characters/` (optionnel)
3. L'application construit automatiquement la base vectorielle au premier lancement

### Modes de jeu

#### Mode MJ Immersif
- Narration interactive
- Génération d'options de jeu
- Suivi des PNJ, lieux, intrigues
- Timeline visuelle
- Différents niveaux de narration

#### Mode Encyclopédique
- Consultation factuelle des règles et de l'univers
- **Réponses longues et détaillées** (300-500 mots minimum)
- **Structure markdown** avec sections (Résumé, Explication, Mécaniques, Exemples, Contexte, Notes)
- **50 chunks de contexte RAG** (vs 20 en mode MJ) pour des réponses exhaustives
- Température optimisée (0.0) pour cohérence et citation fidèle
- **3 options de filtrage des sources** :
  - **📖 Règles uniquement** : Informations détaillées et mécaniques précises (idéal pour comprendre les règles du Tarot des Ombres, combats, etc.)
  - **🌍 Univers uniquement** : Informations générales sur le lore + romans (idéal pour le contexte narratif)
  - **📖🌍 Règles + Univers** (recommandé) : Combine détails techniques et contexte narratif, exclut les romans
- Pas de narration ni d'état de jeu

### Interface

**Sidebar (gauche) - Fiches de personnages**
- Sélecteur de personnage (PDF, TXT, MD)
- Boutons Ouvrir et Télécharger
- **Visualiseur PDF intégré** avec navigation par page (◀ Page X/Y ▶)
- Affichage haute résolution (200 DPI)
- Redimensionnable avec diviseur natif Streamlit

**Zone principale (centre) - Jeu**
- Timeline interactive (mode MJ)
- Chargement du corpus et statistiques
- Zone d'interaction avec le MJ
- Sélection du niveau de narration (Résumé/Détaillé/Immersive)
- Affichage des réponses avec sources RAG
- Historique de la mémoire

**Colonne droite - Configuration**
- Sélection du modèle Ollama
- Choix du mode (MJ immersif / Encyclopédique)
  - **Indicateur "Mode réponses détaillées"** en mode Encyclopédique
  - Affichage du nombre de chunks utilisés (50 en mode Encyclo)
  - **Sélecteur de sources** (en mode Encyclopédique uniquement) :
    - 📖 Règles uniquement : Pour questions techniques sur le système de jeu
    - 🌍 Univers uniquement : Pour questions sur le lore et l'univers narratif
    - 📖🌍 Règles + Univers : Recommandé pour avoir le contexte complet
- Options d'affichage (sources RAG)
- Réglages experts (température, top-p, k retrieval)
- Gestion de la base vectorielle (Recharger/Réinitialiser)
- Sauvegarde/chargement de sessions
- Export Markdown
- Statistiques de session
- État du jeu (PNJ, lieux, intrigues)

### Raccourcis

- **Réglages experts** : Ajuster température, top-p, nombre de chunks RAG
- **Réinitialiser la base** : Reconstruire l'index vectoriel
- **Auto-save** : Sauvegarde automatique tous les 5 messages (configurable)
- **Export Markdown** : Générer un rapport de session

## 🔧 Configuration avancée

### Personnaliser les prompts

Éditer les prompts dans `config.yaml` :

```yaml
prompts:
  mj_system: |
    Tu es le Maître de Jeu...
    [Votre prompt personnalisé]
```

### Optimiser les performances

**Pour les petits corpus (< 100 pages)** :
```yaml
rag:
  chunk_size: 500
  k_retrieval: 4
  k_retrieval_encyclo: 8  # Plus de contexte en mode encyclopédique
```

**Pour les gros corpus (> 500 pages)** :
```yaml
rag:
  chunk_size: 1500
  k_retrieval: 8
  k_retrieval_encyclo: 12  # Plus de contexte en mode encyclopédique
```

**Configuration actuelle (optimisée pour règles détaillées)** :
```yaml
rag:
  chunk_size: 600
  k_retrieval: 20
  k_retrieval_encyclo: 30  # 50% plus de contexte pour réponses exhaustives
```

### Personnaliser le mode encyclopédique

Le mode encyclopédique dispose désormais d'un système de réponses longues optimisé :

**Paramètres dans config.yaml** :
```yaml
rag:
  k_retrieval_encyclo: 50  # Nombre de chunks (défaut: 50, augmenter pour plus de détails)

prompts:
  encyclo_system: |
    Tu es une encyclopédie EXHAUSTIVE...
    [Personnaliser les instructions de structure et longueur]
```

**Ajustements recommandés** :
- Pour des réponses **encore plus longues** : augmenter `k_retrieval_encyclo` à 80-100
- Pour des réponses **plus concises** : réduire à 30 et modifier le prompt système
- La température est automatiquement fixée à **0.0** pour éliminer les hallucinations

### Exemples d'utilisation du mode encyclopédique

**Question sur les règles (utiliser "📖 Règles uniquement")** :
```
Question : "Parle-moi de l'arcane du Tarot des Ombres 'Le Voleur sans Mémoire'"
Filtre : 📖 Règles uniquement

✅ Résultat : Réponse détaillée avec :
- Symbole et signification
- Valeurs de dé (VD), Modificateurs (M), Complications (C)
- Sortilèges typiques avec exemples précis
- Rituels typiques avec calculs de PE
- Citations directes du manuel de règles
```

**Question sur l'univers (utiliser "🌍 Univers uniquement")** :
```
Question : "Qui est le Cardinal de Richelieu dans cet univers ?"
Filtre : 🌍 Univers uniquement

✅ Résultat : Informations narratives sur le personnage, son rôle dans l'histoire
```

**Question mixte (utiliser "📖🌍 Règles + Univers")** :
```
Question : "Comment fonctionne la magie des Lames ?"
Filtre : 📖🌍 Règles + Univers (recommandé)

✅ Résultat : Explication technique (règles) + contexte narratif (univers)
```

### Modèles recommandés

| Modèle | Taille | Usage | Qualité |
|--------|--------|-------|---------|
| `mistral-nemo` | 12B | Équilibré | ⭐⭐⭐⭐ |
| `llama3:70b` | 70B | Meilleure qualité | ⭐⭐⭐⭐⭐ |
| `llama3` | 8B | Rapide | ⭐⭐⭐ |
| `phi3` | 3.8B | Très rapide | ⭐⭐ |
| `qwen2.5:14b` | 14B | Bon compromis | ⭐⭐⭐⭐ |

## 📁 Structure du projet

```
lames-cardinal-mj/
├── app.py                 # Application Streamlit principale
├── config.yaml            # Configuration
├── requirements.txt       # Dépendances
├── README.md             # Documentation
└── core/                 # Modules
    ├── rag.py           # Logique RAG
    ├── memory.py        # Gestion mémoire
    ├── parser.py        # Parsing réponses
    ├── characters.py    # Gestion personnages
    └── utils.py         # Utilitaires
```

## 🐛 Dépannage

### Ollama non trouvé
```bash
# Vérifier qu'Ollama est installé
ollama --version

# Lister les modèles
ollama list

# Télécharger un modèle
ollama pull mistral-nemo
```

### PDF ne s'affiche pas dans la sidebar

**Erreur : "pdf2image non installé ou Poppler manquant"**

1. **Vérifier que pdf2image est installé dans le bon environnement** :
   ```bash
   # Activer le venv si nécessaire
   venv\Scripts\activate  # Windows

   # Installer pdf2image
   pip install pdf2image
   ```

2. **Vérifier que Poppler est installé** :
   - Windows : Télécharger depuis https://github.com/oschwartz10612/poppler-windows/releases
   - Extraire dans un dossier (ex: `D:\IA\poppler-25.07.0`)
   - Vérifier que le dossier `Library\bin` contient des fichiers `.exe`

3. **Configurer le chemin dans `app.py`** (ligne 251) :
   ```python
   poppler_path = r"D:\IA\poppler-25.07.0\Library\bin"  # Votre chemin
   ```

4. **Redémarrer Streamlit** :
   ```bash
   # Arrêter Streamlit (Ctrl+C)
   streamlit run app.py
   ```

### Erreur de mémoire GPU
- Réduire la taille du modèle
- Utiliser CPU : `use_cuda: false` dans `config.yaml`
- Réduire `k_retrieval`

### Base vectorielle corrompue
- Cliquer sur "🗑️ Réinitialiser" dans la colonne Configuration
- Ou supprimer manuellement le dossier `lames_db/`

### Import errors
```bash
# Réinstaller les dépendances
pip install --force-reinstall -r requirements.txt
```

### Erreur "name 'response_text' is not defined"
- Cette erreur a été corrigée dans la version actuelle
- Assurez-vous d'avoir la dernière version du code

## 🎯 Améliorations futures

- [ ] Support de multiples joueurs
- [ ] Génération d'images avec Stable Diffusion
- [ ] API REST pour intégration
- [ ] Mode hors-ligne complet
- [ ] Support audio (TTS/STT)
- [ ] Intégration Discord/Roll20

## 📝 License

MIT License - Voir LICENSE pour plus de détails

## 🤝 Contributions

Les contributions sont les bienvenues ! N'hésite pas à ouvrir une issue ou une pull request.

## 📧 Contact

Pour toute question : [votre-email]

---

**Bon jeu ! 🗡️⚔️**
