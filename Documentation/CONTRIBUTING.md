# Guide de contribution

Merci de ton intérêt pour contribuer au projet Assistant MJ - Les Lames du Cardinal ! 🗡️

## Table des matières

- [Code de conduite](#code-de-conduite)
- [Comment contribuer](#comment-contribuer)
- [Structure du projet](#structure-du-projet)
- [Standards de code](#standards-de-code)
- [Tests](#tests)
- [Processus de Pull Request](#processus-de-pull-request)

## Code de conduite

Ce projet adhère à un code de conduite simple :
- Sois respectueux envers les autres contributeurs
- Accepte les critiques constructives
- Focus sur ce qui est le mieux pour la communauté
- Montre de l'empathie envers les autres

## Comment contribuer

### Rapporter des bugs

Avant de créer un rapport de bug, vérifie qu'il n'existe pas déjà dans les issues.

Pour rapporter un bug, crée une issue avec :
- **Titre clair** décrivant le problème
- **Description détaillée** du comportement attendu vs observé
- **Étapes pour reproduire** le bug
- **Environnement** (OS, version Python, version Ollama, modèle utilisé)
- **Logs d'erreur** si disponibles

### Suggérer des améliorations

Pour suggérer une amélioration :
1. Vérifie qu'elle n'est pas déjà proposée
2. Crée une issue avec le tag "enhancement"
3. Décris clairement la fonctionnalité souhaitée
4. Explique pourquoi elle serait utile
5. Si possible, propose une implémentation

### Contribuer du code

1. **Fork** le projet
2. **Clone** ton fork localement
3. **Crée une branche** : `git checkout -b feature/ma-super-feature`
4. **Développe** ta fonctionnalité
5. **Teste** ton code
6. **Commit** : `git commit -m "feat: ajout de ma super feature"`
7. **Push** : `git push origin feature/ma-super-feature`
8. **Crée une Pull Request**

## Structure du projet

```
lames-cardinal-mj/
├── app.py              # Application principale Streamlit
├── config.yaml         # Configuration
├── setup.py            # Script d'installation
├── core/               # Modules principaux
│   ├── rag.py         # Logique RAG
│   ├── memory.py      # Gestion de la mémoire
│   ├── parser.py      # Parsing des réponses
│   ├── characters.py  # Gestion des personnages
│   └── utils.py       # Utilitaires
└── tests/             # Tests unitaires
    └── test_core.py
```

### Modules

#### `core/rag.py`
Gère tout ce qui concerne le RAG :
- Extraction de documents
- Construction du vectorstore
- Création des chaînes QA

#### `core/memory.py`
Gestion de la mémoire :
- Stockage des échanges
- Limitation de taille
- Persistance
- Gestion des sessions

#### `core/parser.py`
Parsing des réponses LLM :
- Extraction des options
- Extraction des entités (PNJ, lieux, intrigues)
- Gestion de l'état du jeu

#### `core/characters.py`
Gestion des fiches de personnages :
- Chargement des fichiers
- Recherche
- Affichage

#### `core/utils.py`
Fonctions utilitaires diverses

## Standards de code

### Style Python

Nous suivons [PEP 8](https://www.python.org/dev/peps/pep-0008/) avec quelques adaptations :

```python
# Import order
import standard_library
import third_party
from local_module import something

# Classes en PascalCase
class MyClass:
    pass

# Fonctions et variables en snake_case
def my_function(my_parameter):
    my_variable = "value"
    return my_variable

# Constantes en UPPER_CASE
MAX_SIZE = 100

# Type hints recommandés
def process_data(data: str, count: int) -> List[str]:
    pass

# Docstrings pour les fonctions publiques
def important_function(param: str) -> bool:
    """
    Description courte de la fonction.
    
    Args:
        param: Description du paramètre
        
    Returns:
        Description du retour
    """
    pass
```

### Conventions de nommage

- **Fichiers** : `snake_case.py`
- **Classes** : `PascalCase`
- **Fonctions** : `snake_case()`
- **Variables** : `snake_case`
- **Constantes** : `UPPER_CASE`

### Commentaires

- Utilise des docstrings pour les fonctions, classes et modules
- Commente le **pourquoi**, pas le **quoi**
- Garde les commentaires à jour avec le code

```python
# ❌ Mauvais
x = x + 1  # Incrémente x

# ✅ Bon
x = x + 1  # Compense le décalage de l'index
```

### Organisation des imports

```python
# Standard library
import os
import sys
from pathlib import Path

# Third party
import streamlit as st
import pandas as pd

# Local
from core.rag import RAGChain
from core.memory import Memory
```

## Tests

### Écrire des tests

- Chaque nouvelle fonctionnalité doit avoir des tests
- Place les tests dans `tests/`
- Nomme les fichiers `test_*.py`
- Utilise pytest

```python
# tests/test_my_feature.py
import pytest
from core.my_module import my_function

def test_my_function_basic():
    """Test cas de base"""
    result = my_function("input")
    assert result == "expected"

def test_my_function_edge_case():
    """Test cas limite"""
    with pytest.raises(ValueError):
        my_function("")
```

### Lancer les tests

```bash
# Tous les tests
pytest

# Tests spécifiques
pytest tests/test_core.py

# Avec couverture
pytest --cov=core tests/

# Mode verbose
pytest -v
```

### Coverage

Vise au moins 80% de couverture pour le nouveau code.

```bash
pytest --cov=core --cov-report=html
# Ouvre htmlcov/index.html
```

## Processus de Pull Request

### Avant de soumettre

- [ ] Le code suit les standards du projet
- [ ] Les tests passent : `pytest`
- [ ] La documentation est à jour
- [ ] Les commits sont bien formatés
- [ ] Pas de conflits avec `main`

### Format des commits

Utilise [Conventional Commits](https://www.conventionalcommits.org/) :

```
feat: ajout du support multi-joueurs
fix: correction du parsing des options
docs: mise à jour du README
style: formatage du code
refactor: restructuration du module RAG
test: ajout tests pour parser
chore: mise à jour des dépendances
```

### Description de la PR

```markdown
## Description
Brève description des changements

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Comment tester
1. Étape 1
2. Étape 2
3. Résultat attendu

## Checklist
- [ ] Tests ajoutés/mis à jour
- [ ] Documentation mise à jour
- [ ] Code formaté selon les standards
- [ ] Pas de warnings
```

### Review process

1. Un mainteneur review ta PR
2. Si des changements sont demandés, mets à jour la PR
3. Une fois approuvée, elle sera mergée
4. Ta contribution apparaîtra dans le CHANGELOG

## Configuration de développement

### Setup rapide

```bash
# Clone le repo
git clone https://github.com/votre-username/lames-cardinal-mj.git
cd lames-cardinal-mj

# Crée l'environnement
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows

# Installe les dépendances + dev
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Lance les tests
pytest
```

### Outils recommandés

- **IDE** : VS Code, PyCharm
- **Linter** : flake8, pylint
- **Formatter** : black
- **Type checking** : mypy

### VS Code settings

```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true
}
```

## Questions ?

- Crée une issue avec le tag "question"
- Rejoins les discussions
- Consulte la documentation

## Ressources

- [Documentation Streamlit](https://docs.streamlit.io/)
- [LangChain Docs](https://python.langchain.com/)
- [Ollama Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)

---

Merci pour ta contribution ! 🎉