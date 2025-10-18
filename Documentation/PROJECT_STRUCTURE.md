# Structure complète du projet

## 📁 Arborescence

```
lames-cardinal-mj/
│
├── 📄 app.py                      # Application Streamlit principale
├── ⚙️ config.yaml                 # Configuration centralisée
├── 🔧 setup.py                    # Script d'installation interactif
├── 📋 requirements.txt            # Dépendances Python
│
├── 🚀 Scripts de démarrage
│   ├── start.sh                   # Linux/Mac
│   └── start.bat                  # Windows
│
├── 🐳 Docker
│   ├── Dockerfile                 # Image Docker
│   └── docker-compose.yml         # Orchestration
│
├── 📚 Documentation
│   ├── README.md                  # Guide principal
│   ├── CONTRIBUTING.md            # Guide de contribution
│   ├── CHANGELOG.md               # Historique des versions
│   ├── EXAMPLES.md                # Exemples d'utilisation
│   └── PROJECT_STRUCTURE.md       # Ce fichier
│
├── 🧪 Tests
│   └── tests/
│       └── test_core.py           # Tests unitaires
│
├── 🔌 Modules core
│   └── core/
│       ├── __init__.py
│       ├── rag.py                 # Logique RAG (extraction, vectorstore, QA)
│       ├── memory.py              # Gestion de la mémoire et sessions
│       ├── parser.py              # Parsing des réponses LLM
│       ├── characters.py          # Gestion des personnages
│       └── utils.py               # Fonctions utilitaires
│
├── 📂 Données (créés par l'app)
│   └── ~/LamesMJ/                 # Répertoire de base (configurable)
│       ├── Data/                  # PDFs et documents de règles
│       ├── Characters/            # Fiches de personnages
│       ├── lames_db/             # Base vectorielle Chroma
│       ├── saved_sessions/       # Sessions sauvegardées
│       └── memory/               # Mémoire persistante
│
└── 🙈 .gitignore                  # Fichiers à ignorer par Git
```

---

## 📄 Description détaillée des fichiers

### Fichiers principaux

#### `app.py` (Application principale)
**Rôle** : Point d'entrée de l'application Streamlit
- Interface utilisateur complète
- Gestion du layout (sidebar, colonnes)
- Intégration de tous les modules
- Logique de l'application
- Gestion du state

**Fonctions clés** :
- `init_app()` : Initialisation
- `init_session_state()` : État de session
- `render_sidebar()` : Affichage fiches de personnages dans sidebar
- `render_config_panel()` : Panneau de configuration (colonne droite)
- `render_session_manager()` : Gestion des sessions
- `render_statistics()` : Affichage statistiques
- `render_game_state()` : État du jeu (PNJ, lieux, intrigues)
- `render_timeline()` : Timeline interactive
- `render_memory_display()` : Affichage mémoire
- `process_query()` : Traitement des requêtes
- `main()` : Boucle principale

**Organisation de l'interface (v2.1.0)** :
```
┌──────────────────┬────────────────────────────┬─────────────┐
│   SIDEBAR        │    ZONE PRINCIPALE         │   CONFIG    │
│   (Gauche)       │      (Centre)              │  (Droite)   │
│  Redimensionnable│                            │             │
├──────────────────┼────────────────────────────┼─────────────┤
│ 📇 Fiches perso  │ 🗡️ Titre                  │ ⚙️ Config   │
│ [Sélecteur]      │ 🕰️ Timeline               │ Modèle      │
│ 📂 Ouvrir        │ 📚 Chargement corpus       │ Mode        │
│ 💾 Télécharger   │ 💬 Interaction             │ Affichage   │
│ ◀ Page X/Y ▶    │ ✅ Réponse                 │ 🔧 Experts  │
│ [PDF IMAGE]      │ 🧾 Mémoire                 │ 💾 Sessions │
│  200 DPI         │                            │ 📊 Stats    │
│                  │                            │ 🎮 État jeu │
└──────────────────┴────────────────────────────┴─────────────┘
```

#### `config.yaml` (Configuration)
**Rôle** : Configuration centralisée

**Sections** :
- `paths` : Chemins des répertoires
- `model` : Configuration Ollama
- `rag` : Paramètres RAG (embeddings, chunks, k)
- `memory` : Limites de mémoire
- `ui` : Paramètres d'interface
- `prompts` : Prompts système personnalisables
- `advanced` : Options avancées

**Avantage** : Modification sans toucher au code

#### `requirements.txt` (Dépendances)
**Rôle** : Liste des packages Python nécessaires

**Catégories** :
- Core : streamlit, pyyaml
- LangChain : langchain, langchain-community, langchain-ollama
- RAG : chromadb, sentence-transformers
- PDF extraction : pdfplumber, PyPDF2
- PDF rendering : pdf2image, Pillow (nécessite Poppler)
- Visualisation : plotly, pandas
- Optionnel : torch (GPU)

#### `setup.py` (Installation)
**Rôle** : Script interactif de première installation

**Actions** :
- Vérification Python et Ollama
- Création de la structure de répertoires
- Génération du config.yaml
- Installation des dépendances
- Téléchargement de modèles Ollama

---

### Modules core/

#### `core/rag.py` (RAG)
**Classes** :
- `DocumentExtractor` : Extraction de texte (PDF, TXT, MD)
- `VectorStore` : Gestion Chroma + embeddings
- `RAGChain` : Création et gestion des chaînes QA

**Fonctionnalités** :
- Extraction multi-formats
- Chunking intelligent
- Support CUDA/CPU
- Cache et lazy loading
- Création de prompts contextuels

#### `core/memory.py` (Mémoire)
**Classes** :
- `MemoryEntry` : Représente un échange
- `Memory` : Gestion de la mémoire avec limite
- `SessionManager` : Sauvegarde/chargement de sessions
- `Statistics` : Statistiques de session

**Fonctionnalités** :
- Limitation automatique de taille
- Persistance JSON
- Format pour prompts
- Horodatage
- Auto-save

#### `core/parser.py` (Parsing)
**Classes** :
- `ParsedResponse` : Résultat du parsing
- `ResponseParser` : Extraction d'éléments structurés
- `GameState` : État du jeu (PNJ, lieux, intrigues)

**Fonctionnalités** :
- Extraction d'options (patterns multiples)
- Extraction d'entités ([PNJ:...], [Lieu:...], etc.)
- Gestion des icônes
- Sérialisation état du jeu

#### `core/characters.py` (Personnages)
**Classes** :
- `Character` : Représente un personnage
- `CharacterManager` : Gestion des fiches

**Fonctionnalités** :
- Chargement multi-formats
- Cache intelligent
- Recherche dans les fiches
- Export groupé

#### `core/utils.py` (Utilitaires)
**Fonctions** :
- `load_config()` : Charge config.yaml
- `get_ollama_models()` : Liste modèles Ollama
- `validate_ollama_installation()` : Vérifie Ollama
- `format_file_size()` : Formatage tailles
- `truncate_text()` : Troncature intelligente
- `export_session_to_markdown()` : Export MD
- `ColorScheme` : Thème visuel

---

### Scripts de démarrage

#### `start.sh` (Linux/Mac)
**Rôle** : Démarrage rapide Unix

**Actions** :
- Vérifications (Python, venv, Ollama)
- Création/activation venv
- Installation dépendances
- Validation config
- Lancement Streamlit

**Options** :
```bash
./start.sh           # Démarrage normal
./start.sh --setup   # Setup complet
./start.sh --check   # Vérification seulement
./start.sh --help    # Aide
```

#### `start.bat` (Windows)
**Rôle** : Équivalent Windows du start.sh

**Fonctionnalités** : Identiques à start.sh mais syntaxe Windows

---

### Docker

#### `Dockerfile`
**Rôle** : Image Docker de l'application

**Caractéristiques** :
- Base Python 3.11-slim
- Utilisateur non-root (sécurité)
- Healthcheck intégré
- Port 8501 exposé
- Optimisé pour production

#### `docker-compose.yml`
**Rôle** : Orchestration multi-containers

**Services** :
- `mj-assistant` : Application principale
- `ollama` (optionnel) : Serveur Ollama

**Volumes** :
- Montage des données persistantes
- Config en lecture seule

---

### Documentation

#### `README.md`
**Contenu** :
- Présentation du projet
- Fonctionnalités
- Installation détaillée
- Utilisation
- Configuration
- Dépannage
- FAQ

#### `CONTRIBUTING.md`
**Contenu** :
- Code de conduite
- Comment contribuer
- Standards de code
- Tests
- Process de PR
- Setup développement

#### `CHANGELOG.md`
**Contenu** :
- Historique des versions
- Changements par catégorie
- Notes de migration
- Bugs connus

#### `EXAMPLES.md`
**Contenu** :
- Exemples concrets d'utilisation
- Scénarios de jeu
- Configurations personnalisées
- Bonnes pratiques
- Tips & tricks

---

### Tests

#### `tests/test_core.py`
**Classes de tests** :
- `TestMemory` : Tests mémoire
- `TestParser` : Tests parsing
- `TestGameState` : Tests état du jeu
- `TestUtils` : Tests utilitaires
- `TestSessionManager` : Tests sessions

**Coverage** : Vise 80%+ sur les modules core

**Exécution** :
```bash
pytest                    # Tous les tests
pytest tests/test_core.py # Tests core
pytest --cov=core         # Avec coverage
```

---

### Configuration Git

#### `.gitignore`
**Rôle** : Exclut fichiers sensibles/générés

**Exclusions** :
- Python : `__pycache__`, `*.pyc`, venv
- IDE : `.vscode`, `.idea`
- Données : PDFs, sessions, mémoire, vectordb
- Logs et temporaires
- OS : `.DS_Store`, `Thumbs.db`

---

## 🔄 Flux de données

```
[PDFs] → DocumentExtractor → VectorStore (Chroma)
                                    ↓
[User Query] → RAGChain → Retriever → LLM (Ollama)
                                    ↓
[Response] → ResponseParser → GameState
                    ↓
              Memory → Persistence
```

---

## 🚀 Démarrage rapide

### Option 1 : Installation complète
```bash
python setup.py
./start.sh  # ou start.bat sur Windows
```

### Option 2 : Manuel
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Option 3 : Docker
```bash
docker-compose up -d
# Accès: http://localhost:8501
```

---

## 📊 Statistiques du projet

- **Lignes de code** : ~2500+ lignes Python
- **Modules** : 5 modules core
- **Tests** : 30+ tests unitaires
- **Documentation** : 1000+ lignes
- **Fichiers** : 20+ fichiers

---

## 🎯 Points d'entrée par use-case

### Je veux...

**...installer l'app**
→ `setup.py` puis `start.sh`

**...comprendre le code**
→ `README.md` puis modules `core/`

**...contribuer**
→ `CONTRIBUTING.md`

**...voir des exemples**
→ `EXAMPLES.md`

**...modifier la config**
→ `config.yaml`

**...lancer l'app**
→ `start.sh` / `start.bat` / `app.py`

**...écrire des tests**
→ `tests/test_core.py`

**...déployer en production**
→ `Dockerfile` + `docker-compose.yml`

---

## 🔧 Maintenance

### Mise à jour des dépendances
```bash
pip install --upgrade -r requirements.txt
```

### Nettoyage
```bash
# Supprimer cache Python
find . -type d -name "__pycache__" -exec rm -rf {} +

# Réinitialiser vectordb
rm -rf ~/LamesMJ/lames_db/*
```

### Backup
```bash
# Sauvegarder les données importantes
tar -czf backup.tar.gz ~/LamesMJ/saved_sessions ~/LamesMJ/memory
```

---

## 📈 Évolutions futures possibles

- [ ] API REST
- [ ] Support multi-joueurs temps réel
- [ ] Génération d'images (Stable Diffusion)
- [ ] TTS/STT pour voice control
- [ ] Intégration Discord/Roll20
- [ ] Mode campagne avec arcs narratifs
- [ ] Système de quêtes automatique
- [ ] Fine-tuning de modèles personnalisés

---

## 🤝 Contributions

Toutes les contributions sont bienvenues ! Consulte `CONTRIBUTING.md` pour les détails.

---

**Version** : 2.0.0  
**Dernière mise à jour** : 2025-01-XX  
**Licence** : MIT