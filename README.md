# Assistant MJ — Les Lames du Cardinal

Assistant intelligent pour Maître de Jeu basé sur un LLM local (Ollama) pour le jeu de rôle "Les Lames du Cardinal". Deux modes distincts : narration créative et consultation encyclopédique des règles.

## Fonctionnalités

- **Mode MJ Immersif** : LLM créatif sans RAG — narration immersive, improvisation, atmosphère XVIIe siècle baroque. Le MJ s'inspire de l'univers et des livres, les règles mécaniques sont secondaires.
- **Mode Encyclopédique** : RAG (Retrieval-Augmented Generation) sur les PDFs de règles — réponses factuelles et précises avec citations de sources.
- **Recherche hybride** : BM25 (mots-clés) + vectoriel (sémantique) + re-ranking CrossEncoder
- **Chunking par page** : une page PDF = un chunk, sans contamination inter-pages
- **Enrichissement VD** : reconstruction automatique des titres d'arcanes manquants
- **Prompts éditables à la volée** : dans `prompts/` sans redémarrer l'app
- **Mémoire contextuelle** : suivi des échanges avec limite intelligente
- **Timeline interactive** : visualisation de la progression de la partie
- **Gestion de personnages** : affichage des fiches (PDF, TXT, MD)
- **Sessions sauvegardables** : sauvegarde et chargement de parties
- **Multi-modèles** : changement de modèle Ollama à la volée

## Prérequis

1. **Python 3.9+**
2. **Ollama** installé et en cours d'exécution
   - Installation : https://ollama.ai
   - Télécharger un modèle : `ollama pull mistral-nemo`
3. **Poppler** (pour l'affichage PDF dans la sidebar)
   - Windows : https://github.com/oschwartz10612/poppler-windows/releases
   - Linux : `sudo apt-get install poppler-utils`
   - macOS : `brew install poppler`

## Installation

```bash
# Cloner le projet
git clone <repo>
cd lames-cardinal-mj

# Environnement virtuel
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# Dépendances
pip install -r requirements.txt

# GPU (optionnel) — RTX 50xx / CUDA 12.8
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

**Poppler sur Windows** : extraire l'archive dans un dossier (ex: `D:\IA\poppler-25.07.0`) puis configurer le chemin dans `app.py`.

## Structure du projet

```
MJ-Assistant/
├── app.py              # Point d'entrée Streamlit
├── app_init.py         # Logique de traitement des requêtes
├── app_ui.py           # Composants UI réutilisables
├── app_memory.py       # Utilitaires mémoire UI
├── config.yaml         # Configuration générale
├── requirements.txt    # Dépendances Python
│
├── prompts/            # Prompts système — éditables sans redémarrer
│   ├── mj_system.txt       # Prompt du mode MJ immersif
│   └── encyclo_system.txt  # Prompt du mode Encyclopédique
│
├── core/               # Modules métier
│   ├── rag.py          # Pipeline RAG (extraction, chunking, vectorisation, re-ranking)
│   ├── memory.py       # Gestion mémoire et sessions
│   ├── parser.py       # Parsing des réponses LLM
│   ├── characters.py   # Gestion des fiches de personnages
│   └── utils.py        # Utilitaires
│
├── Data/               # PDFs de règles et d'univers
├── Characters/         # Fiches de personnages (.txt, .md, .pdf)
├── lames_db/           # Base vectorielle Chroma (auto-générée)
├── saved_sessions/     # Sessions sauvegardées
└── memory/             # Mémoire persistante
```

## Lancement

```bash
streamlit run app.py
```

Au premier lancement, l'app construit automatiquement la base vectorielle depuis les PDFs dans `Data/`.

Pour reconstruire la base (après ajout de PDFs ou changement de chunking) : supprimer `lames_db/` et relancer.

## Modes de jeu

### Mode MJ Immersif

LLM créatif **sans RAG**. Le modèle narre librement en s'appuyant sur le prompt système (`prompts/mj_system.txt`) et l'historique de la conversation.

- Narration au présent, à la deuxième personne
- Atmosphère Paris XVIIe siècle, cape et épée, magie secrète
- PNJ avec voix distinctes, descriptions sensorielles
- Improvisation cohérente avec l'univers des Lames du Cardinal
- Pas de sources citées, pas de contrainte factuelle stricte

Pour les questions sur les règles précises, utiliser le mode Encyclopédique.

### Mode Encyclopédique

RAG two-phase sur les PDFs de règles :
1. Récupération large (50 chunks, BM25 + vectoriel)
2. Re-ranking CrossEncoder → 8 meilleurs chunks
3. Réponse LLM avec citations `(Réf.X)` et température 0.0

**Filtres de sources disponibles :**
- `Règles uniquement` — manuels de règles, détails mécaniques
- `Univers uniquement` — lore, romans
- `Règles + Univers` (défaut) — combiné, sans romans

## Personnaliser les prompts

Éditer directement les fichiers dans `prompts/` — l'effet est immédiat à la prochaine requête, sans redémarrer Streamlit.

```
prompts/mj_system.txt       ← style narratif, univers, consignes MJ
prompts/encyclo_system.txt  ← format des réponses encyclopédiques
```

Les valeurs dans `config.yaml` (section `prompts:`) servent de fallback si les fichiers sont absents.

## Configuration

`config.yaml` — principaux paramètres ajustables :

```yaml
model:
  default: "mistral-nemo"   # Modèle Ollama par défaut
  temperature: 0.7          # Température MJ (0.0 en mode encyclo)
  num_ctx: 32768            # Taille du contexte

rag:
  embedding_model: "BAAI/bge-m3"
  k_retrieval_encyclo: 50   # Chunks récupérés avant re-ranking
  chunk_size: 2000          # Taille max d'un chunk (par page)
  use_cuda: true            # GPU pour les embeddings
  enable_reranking: true    # Re-ranking CrossEncoder
```

## Modèles recommandés

| Modèle | Taille | Usage |
|--------|--------|-------|
| `mistral-nemo` | 12B | Bon équilibre qualité/vitesse |
| `qwen2.5:14b` | 14B | Excellent en français |
| `llama3:70b` | 70B | Meilleure qualité |
| `phi3` | 3.8B | Très rapide, qualité réduite |

## Dépannage

**Base vectorielle à reconstruire** : supprimer `lames_db/` et relancer.

**Ollama non trouvé** :
```bash
ollama --version
ollama list
ollama pull mistral-nemo
```

**PDF ne s'affiche pas** : vérifier que Poppler est installé et que le chemin est configuré dans `app.py`.

**Erreur GPU / mémoire** : passer à `use_cuda: false` dans `config.yaml`.

**Réinstaller les dépendances** :
```bash
pip install --force-reinstall -r requirements.txt
```

## Licence

MIT
