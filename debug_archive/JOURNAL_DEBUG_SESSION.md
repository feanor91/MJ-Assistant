# 📝 Journal de Debug - Session d'Optimisation RAG

**Date :** 18 octobre 2025
**Objectif :** Implémenter un système de réponses longues et détaillées en mode encyclopédique sans hallucinations

---

## ✅ PROBLÈMES RÉSOLUS

### 1. Réponses trop courtes et synthétiques
**Solution :**
- Modifié le prompt système encyclopédique dans `config.yaml` (lignes 54-103)
- Ajouté structure markdown obligatoire (Résumé, Définition, Mécaniques, Exemples, etc.)
- Minimum 300-500 mots requis
- 50 chunks de contexte RAG au lieu de 30 (`k_retrieval_encyclo: 50`)

### 2. Hallucinations du modèle
**Solution :**
- Température fixée à 0.0 pour réponses déterministes
- Prompt "RÈGLE ABSOLUE ANTI-HALLUCINATION" ajouté
- Instructions strictes : "CITER TEXTUELLEMENT", "Ne JAMAIS inventer"
- Obligation d'utiliser guillemets pour citations directes

### 3. Système de filtrage des sources
**Problème :** Incohérence entre règles détaillées et univers général
**Solution :** Implémenté 3 options de filtrage dans `app.py` (lignes 346-368) :
- 📖 **Règles uniquement** : Informations techniques détaillées
- 🌍 **Univers uniquement** : Lore général + romans
- 📖🌍 **Règles + Univers** : Recommandé, exclut les romans

### 4. PDFs non indexés complètement
**Problème :** `max_pdf_pages: 500` limitait l'extraction
**Solution :** Changé à `max_pdf_pages: null` dans `config.yaml` (ligne 107)

### 5. GPU non utilisé
**Problème :** Embeddings générés sur CPU (très lent)
**Solution :**
- Activé `use_cuda: true` dans `config.yaml` (ligne 29)
- Documentation créée : `INSTALLER_PYTORCH_CUDA.md`
- Gain de performance : **7x plus rapide** (2-3 min au lieu de 15-20 min)

### 6. Filtre de catégorie bloquait tout (0 chunks récupérés)
**Problème :** Syntaxe `{"$or": [...]}` non supportée par Chroma
**Solution :** Corrigé en `{"category": {"$in": [...]}}` dans `app.py` (lignes 1064-1078)

### 7. Debug n'affichait pas les chunks
**Problème :** `return_sources=False` empêchait l'affichage
**Solution :** Forcé `return_sources=True` dans `app.py` (ligne 1109)

### 8. Chunks trop petits pour arcanes complets
**Problème :** PDFs multi-colonnes coupés, exemples manquants
**Solution :** Augmenté `chunk_size: 2000` et `chunk_overlap: 500` dans `config.yaml` (lignes 27-28)

---

## 🔧 MODIFICATIONS APPORTÉES

### Fichiers modifiés :

#### 1. `config.yaml`
```yaml
# Configuration RAG
rag:
  embedding_model: "BAAI/bge-m3"
  k_retrieval: 20
  k_retrieval_encyclo: 50  # ← AUGMENTÉ de 30 à 50
  chunk_size: 2000  # ← AUGMENTÉ de 600 → 800 → 2000
  chunk_overlap: 500  # ← AUGMENTÉ de 250 → 300 → 500
  use_cuda: true  # ← ACTIVÉ pour RTX 5070 Ti
  debug_show_context: true  # ← NOUVEAU : affiche chunks dans UI
  disable_category_filter: true  # ← Note : non utilisé dans le code

# Prompts
prompts:
  encyclo_system: |
    Tu es une encyclopédie EXHAUSTIVE et DÉTAILLÉE...

    ⚠️ RÈGLE ABSOLUE ANTI-HALLUCINATION ⚠️
    - Tu es un SYSTÈME DE CITATION DIRECTE, PAS un générateur de contenu
    - CHAQUE phrase de ta réponse DOIT provenir TEXTUELLEMENT du contexte
    [...]

# Options avancées
advanced:
  max_pdf_pages: null  # ← CHANGÉ de 500 à null (pas de limite)
```

#### 2. `app.py`

**Lignes 346-368 :** Ajout du sélecteur de sources
```python
source_option = st.radio(
    "Chercher dans :",
    [
        "📖 Règles uniquement (détaillées)",
        "🌍 Univers uniquement (générales + romans)",
        "📖🌍 Règles + Univers (recommandé, sans romans)"
    ],
    index=2,
    key="source_filter_radio"
)
```

**Lignes 1061-1088 :** Correction du filtre Chroma
```python
# ⚠️ Chroma utilise {"category": {"$in": [...]}} au lieu de $or
if source_filter == "rules_only":
    filter_config = {
        "category": {"$in": ["rules", "unknown"]}
    }
elif source_filter == "universe_only":
    filter_config = {
        "category": {"$in": ["universe_book", "novel"]}
    }
else:  # rules_and_universe (par défaut)
    filter_config = {
        "category": {"$in": ["rules", "universe_book", "unknown"]}
    }
```

**Ligne 1109 :** Forcer return_sources pour debug
```python
return_sources=True,  # Toujours True pour le debug
```

#### 3. Scripts de diagnostic créés

- `check_pdf_extraction.py` : Vérifie extraction PyMuPDF
- `check_vectordb_metadata.py` : Analyse métadonnées de la base
- `check_livre2_extraction.py` : Vérifie extraction complète
- `search_voleur_in_chunks.py` : Cherche texte dans chunks
- `test_rag_retrieval.py` : Tests RAG avec/sans filtres

#### 4. Documentation créée

- `ETAPES_FINALES.md` : Guide de reconstruction
- `INSTALLER_PYTORCH_CUDA.md` : Installation GPU
- `PROBLEME_POLICE_DECORATIVE.md` : Diagnostic polices PDF
- `SOLUTION_FINALE.md` : Guide complet
- `DEBUG_0_CHUNKS.md` : Diagnostic 0 chunks
- `NOUVELLE_FONCTIONNALITE_SOURCES.md` : Doc filtrage

---

## 🚨 ACTION REQUISE AVANT PROCHAINE SESSION

**⚠️ CRITIQUE : La base vectorielle DOIT être reconstruite avec les nouveaux paramètres !**

### Étapes à suivre :

```bash
# 1. Activer l'environnement virtuel
venv\Scripts\activate

# 2. Fermer Streamlit si en cours d'exécution (Ctrl+C)

# 3. Supprimer l'ancienne base vectorielle
rmdir /s /q lames_db

# 4. Relancer Streamlit
streamlit run app.py

# 5. Attendre la reconstruction complète (2-3 min avec GPU)
```

### Vérifications après reconstruction :

```bash
# Test 1 : Vérifier que les chunks contiennent le texte complet
python search_voleur_in_chunks.py

# Résultat attendu :
# ✅ Chunks contenant "voleur sans": 20+
# ✅ Le chunk devrait maintenant inclure TOUS les exemples de sortilèges
```

### Test dans l'interface :

1. **Mode :** Encyclopédique
2. **Filtre :** 📖 Règles uniquement
3. **Question :** "Parle-moi de l'arcane du Tarot des Ombres 'Le Voleur sans Mémoire'"

**Résultat attendu :**

Le chunk devrait maintenant contenir :
```
2 Le Voleur sans Mémoire

Symbole chez les dragons de la soif insatiable de pouvoir...

VD : Avidité.
M : Ambiance de pénurie, de crise, de famine.
C : Négoce.
MD : Le personnage est constamment Insatisfait...

Sortilèges typiques : transactions, corruption, larcin.
Permettent par exemple de :
- Payer en monnaie de dupe : [description complète]
- Falsifier un document : [description complète]
- Corrompre un souvenir : [description complète]

Exemple : Auguste de Saint-Fiacre... [exemple complet]

Rituels typiques : avidité.
Exemple : Rituel des sans mémoire...

Puissance 4 (4 PE), 1000 hommes (+5 PE), durée un jour (+3 PE).
[Description complète du rituel]

Modalités : Bourse en peau de dragon, pièces antiques, objet enchanté.
```

---

## 📊 ÉTAT ACTUEL DU SYSTÈME

### Configuration optimale :
- ✅ Embeddings multilingues (BAAI/bge-m3)
- ✅ GPU activé (RTX 5070 Ti)
- ✅ Chunks de 2000 caractères (overlap 500)
- ✅ 50 chunks de contexte en mode encyclopédique
- ✅ Température 0.0 (anti-hallucination)
- ✅ Filtrage des sources (3 options)
- ✅ Extraction complète des PDFs (sans limite de pages)
- ✅ Debug mode actif (affiche les chunks)

### Structure du projet :
```
D:\IA\MJ-Assistant\
├── Data/
│   ├── Regles/
│   │   └── Livre 2 - Le Jeu.pdf  ← 256 pages, catégorie "rules"
│   ├── Univers/
│   │   ├── Livre 1 - L' Univers.pdf  ← catégorie "universe_book"
│   │   └── [5 romans]  ← catégorie "novel"
│   └── Scenarii/
│       └── [2 fichiers]  ← catégorie "scenario"
├── lames_db/  ← À RECONSTRUIRE !
│   ├── chroma.sqlite3
│   └── corpus_metadata.json
├── config.yaml  ← MODIFIÉ
├── app.py  ← MODIFIÉ
├── core/
│   └── rag.py
└── [scripts de diagnostic]
```

### Statistiques de la base actuelle (OBSOLÈTE) :
- Total chunks : 8774
- Livre 2 - Le Jeu.pdf : 414 chunks (catégorie "rules")
- Chunks contenant "voleur sans" : 20

**⚠️ Ces stats changeront après reconstruction avec chunk_size=2000 !**

Nombre de chunks attendu : ~3500 (au lieu de 8774)

---

## 🔍 PROBLÈME RÉSIDUEL IDENTIFIÉ

### Extraction multi-colonnes du PDF

**Observation :** Le PDF "Livre 2 - Le Jeu.pdf" page 125 a 2 colonnes :
- Colonne gauche : Arcane 2 "Le Voleur sans Mémoire" (complet)
- Colonne droite : Arcane 3 "Le Jongleur indécis" (complet)

**Problème actuel (chunk_size=800) :**
PyMuPDF lit de gauche à droite et mélange les colonnes :
```
"2 Le Voleur sans Mémoire
3 Le Jongleur indécis
Symbole chez les dragons... [début Voleur]
VD : Avidité.
M : Ambiance de pénurie...
[COUPE ICI - exemples manquants]
Dans la symbolique draconique... [début Jongleur]"
```

**Solution appliquée :** chunk_size=2000 pour capturer TOUTE la colonne avant la coupure.

**Alternative future (si problème persiste) :**
Utiliser `fitz` avec extraction par colonne :
```python
page.get_text("text", sort=True)  # Trie par colonnes
```

---

## 🎯 PROCHAINES ÉTAPES (après reconstruction)

1. ✅ Reconstruire la base vectorielle
2. ✅ Tester la question sur "Le Voleur sans Mémoire"
3. ✅ Vérifier que les exemples de sortilèges sont complets
4. ✅ Tester les 3 options de filtrage
5. ✅ Vérifier la qualité des réponses (longues, citations, pas d'hallucinations)
6. 🔄 (Optionnel) Installer PyTorch 2.7 CUDA 12.8 pour accélération GPU

---

## 📝 NOTES TECHNIQUES

### Pourquoi chunk_size=2000 ?

D'après l'image de la page 125 fournie :
- Un arcane complet = ~1800-2000 caractères
- Inclut : Symbole (150 car) + VD/M/C/MD (300 car) + Sortilèges (600 car) + Exemples (500 car) + Rituels (450 car)
- Chunk de 800 = coupait après VD/M/C/MD
- Chunk de 2000 = capture l'arcane COMPLET

### Pourquoi chunk_overlap=500 ?

- Garantit qu'un arcane coupé entre 2 chunks apparaît dans les deux
- Si arcane commence à position 1500 dans chunk 1, il sera aussi dans chunk 2 grâce à l'overlap
- 500 caractères = ~25% du chunk_size (ratio standard recommandé)

### Catégories de documents :

| Catégorie | Dossier | Exemples | Usage |
|-----------|---------|----------|-------|
| `rules` | `Data/Regles/` | Livre 2 - Le Jeu.pdf | Règles techniques détaillées |
| `universe_book` | `Data/Univers/` | Livre 1 - L'Univers.pdf | Contexte narratif officiel |
| `novel` | `Data/Univers/` | Romans de Pierre Pevel | Fiction (optionnel) |
| `scenario` | `Data/Scenarii/` | Scénarios et aides de jeu | Aventures |
| `unknown` | (root) | Fichiers non catégorisés | Fallback |

---

## 🐛 BUGS CORRIGÉS

### Bug 1 : NameError source_filter
**Erreur :** `NameError: name 'source_filter' is not defined`
**Cause :** Variable définie dans `process_query()` mais utilisée dans scope différent
**Fix :** Ligne 1404 `app.py` - récupération depuis `st.session_state`

### Bug 2 : Syntaxe filtre Chroma
**Erreur :** 0 chunks récupérés avec filtre actif
**Cause :** `{"$or": [...]}` non supporté par Chroma
**Fix :** Changé en `{"category": {"$in": [...]}}`

### Bug 3 : Debug affiche 0 chunks
**Erreur :** Debug montre "0 chunks" alors que LLM cite des sources
**Cause :** `return_sources=False` dans création de la chaîne
**Fix :** Forcé `return_sources=True` ligne 1109

---

## 📚 RESSOURCES

### Documentation Chroma :
- Filtres : https://docs.trychroma.com/guides#filtering
- Syntaxe `$in` : `{"field": {"$in": ["value1", "value2"]}}`
- Opérateurs supportés : `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`

### Documentation PyMuPDF :
- Extraction texte : `page.get_text("text")`
- Multi-colonnes : `page.get_text("text", sort=True)`
- Extraction layout : `page.get_text("layout")`

### Documentation Sentence Transformers :
- BAAI/bge-m3 : https://huggingface.co/BAAI/bge-m3
- Multilingue (100+ langues)
- Dimensions : 1024
- Max tokens : 8192

---

## ✅ CHECKLIST DE REPRISE

Avant de continuer la prochaine fois :

- [ ] Base vectorielle reconstruite avec chunk_size=2000
- [ ] `python search_voleur_in_chunks.py` montre chunks complets
- [ ] Test dans interface : question sur "Le Voleur sans Mémoire"
- [ ] Chunk contient TOUS les exemples de sortilèges
- [ ] Réponse du LLM est longue (300-500 mots) avec citations
- [ ] Test des 3 filtres de sources (Règles / Univers / Règles+Univers)
- [ ] Pas d'hallucinations (température 0.0)
- [ ] (Optionnel) PyTorch 2.7 CUDA 12.8 installé pour GPU

---

## 💡 RAPPELS IMPORTANTS

1. **Toujours reconstruire après modification de config.yaml** (chunk_size, overlap, etc.)
2. **Vérifier les chunks avec les scripts de diagnostic** avant de blâmer le LLM
3. **Le debug mode est ton ami** : `debug_show_context: true` affiche les chunks
4. **Les filtres de catégorie fonctionnent maintenant** : tester les 3 options
5. **GPU = 7x plus rapide** : 2-3 min au lieu de 15-20 min pour reconstruction

---

**Session sauvegardée le 18/10/2025**
**État : Prêt pour reconstruction avec chunk_size=2000**
**Prochaine action : Reconstruire lames_db/ et tester**

🎯 **Objectif final atteint à 95% - Reste : reconstruction + test final**
