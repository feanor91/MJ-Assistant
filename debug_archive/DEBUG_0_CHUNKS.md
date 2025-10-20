# 🔍 DEBUG : 0 chunks récupérés

## Problème
Le mode encyclopédique retourne **0 chunks**, ce qui signifie que le RAG ne trouve RIEN dans la base vectorielle.

## 🧪 Diagnostic en 3 étapes

### Étape 1 : Lancer le script de test

```bash
# Active ton environnement virtuel
venv\Scripts\activate  # Windows
# ou
source venv/bin/activate  # Linux/Mac

# Lance le script de diagnostic
python test_rag_retrieval.py
```

Ce script va tester **2 scénarios** :
1. **TEST 1** : Recherche SANS filtre (récupération brute)
2. **TEST 2** : Recherche AVEC filtre de catégorie (mode encyclopédique)

### Étape 2 : Analyser les résultats

#### Cas A : TEST 1 trouve des chunks, TEST 2 trouve 0 chunks
**Diagnostic** : Le filtre de catégorie bloque tout
**Cause** : Les documents sont mal catégorisés ou le filtre est trop restrictif
**Solution** : Désactive temporairement le filtre

Dans `config.yaml`, ligne 31 :
```yaml
disable_category_filter: true
```

Puis relance l'application et reteste.

---

#### Cas B : TEST 1 trouve 0 chunks, TEST 2 trouve 0 chunks
**Diagnostic** : La base vectorielle est vide ou corrompue
**Cause** : Base non construite ou reconstruction nécessaire
**Solution** : Réinitialise complètement la base

```bash
# Ferme Streamlit (Ctrl+C)
# Supprime le dossier
rmdir /s /q lames_db     # Windows
# ou
rm -rf lames_db          # Linux/Mac

# Relance l'app (reconstruction auto)
streamlit run app.py
```

---

#### Cas C : TEST 1 et TEST 2 trouvent des chunks mais SANS le texte recherché
**Diagnostic** : Les embeddings trouvent des chunks non pertinents
**Cause** :
- Chunking trop petit/grand
- Embeddings pas assez performants pour le français
- Question mal formulée

**Solutions** :
1. Vérifie que ton PDF sur le Tarot des Ombres est bien dans `Data/`
2. Augmente encore `k_retrieval_encyclo` à 80 ou 100
3. Essaye une question plus directe : "Voleur sans mémoire"

---

#### Cas D : Les chunks contiennent le bon texte mais le modèle hallucine quand même
**Diagnostic** : Problème de prompt/modèle
**Cause** : Le modèle ne suit pas les instructions de citation
**Solutions** :
1. Essaye un autre modèle : `llama3.2`, `qwen2.5:14b`, `mistral-nemo`
2. Vérifie que température = 0.0 en mode encyclopédique
3. Le prompt est déjà ultra-strict, mais certains modèles hallucinent quand même

---

### Étape 3 : Vérifier la structure des dossiers

Assure-toi que ta structure est correcte :

```
MJ-Assistant/
├── Data/
│   └── Regles/              ← Le PDF doit être ICI (ou dans Data/ directement)
│       └── Lames_Cardinal_Regles.pdf
├── lames_db/                ← Base vectorielle (générée auto)
│   ├── chroma.sqlite3
│   └── corpus_metadata.json
└── config.yaml
```

Si ton PDF sur le Tarot des Ombres est dans `Data/Regles/`, il sera catégorisé comme `"rules"` et passera le filtre.

Si ton PDF est directement dans `Data/` (pas de sous-dossier), il sera catégorisé comme `"unknown"` et passera AUSSI le filtre (on a ajouté "unknown" dans le code).

---

## 🔧 Solutions rapides

### Solution 1 : Désactiver le filtre complètement

Dans `config.yaml` :
```yaml
rag:
  disable_category_filter: true
```

### Solution 2 : Augmenter drastiquement k

Dans `config.yaml` :
```yaml
rag:
  k_retrieval_encyclo: 100  # Au lieu de 50
```

### Solution 3 : Réinitialiser avec nouveaux paramètres

1. Ferme Streamlit
2. Supprime `lames_db/`
3. Dans `config.yaml`, vérifie :
   ```yaml
   chunk_size: 800
   chunk_overlap: 300
   k_retrieval_encyclo: 50
   ```
4. Relance : `streamlit run app.py`
5. Attends la reconstruction complète (5-10 min)

---

## 📊 Mode DEBUG dans l'interface

Une fois le problème potentiellement résolu, teste dans l'interface :

1. Lance l'app : `streamlit run app.py`
2. Mode : **Encyclopédique**
3. Pose la question : "Parle-moi de l'arcane du Tarot des ombres le Voleur sans mémoire"
4. Ouvre l'expander : **"🔍 DEBUG: Contexte RAG complet"**
5. Vérifie les 50 chunks affichés

**Ce que tu devrais voir** :
- Source : Le nom de ton PDF de règles
- Catégorie : `rules` (ou `unknown`)
- Contenu : Le texte exact sur le Voleur sans Mémoire

**Si les chunks sont bons** → Le modèle devrait citer correctement avec température 0
**Si les chunks sont mauvais** → Augmente k ou reconstruit la base avec des chunks plus gros

---

## 💡 Pourquoi NotebookLM fonctionne mieux ?

NotebookLM utilise probablement :
1. **Des chunks adaptatifs** (segmentation intelligente par section)
2. **Des embeddings multimodaux** (texte + structure)
3. **Un reranking** (reclassement des résultats)
4. **Une température plus stricte** par défaut
5. **Un prompt system ultra-contraignant**

Notre système est bon mais peut nécessiter du tuning selon ton corpus spécifique.

---

## 📞 Si rien ne fonctionne

Envoie-moi les résultats du script `test_rag_retrieval.py` :
- Nombre de chunks trouvés dans TEST 1 et TEST 2
- Les 3 premiers chunks affichés
- Les catégories détectées

Cela permettra de diagnostiquer précisément le problème.
