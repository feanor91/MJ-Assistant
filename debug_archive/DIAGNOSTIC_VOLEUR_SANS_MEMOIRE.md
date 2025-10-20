# 🔍 Diagnostic : "Le Voleur sans Mémoire" non trouvé

## ❌ Problème actuel

Le système répond : **"Il n'y a pas d'information sur un arcane appelé 'Le Voleur sans Mémoire'"**

Cela signifie que **les chunks récupérés ne contiennent pas le texte recherché**.

## 🧪 Diagnostic en 3 étapes

### Étape 1 : Lance le script de test amélioré

```bash
# Active l'environnement virtuel
venv\Scripts\activate

# Lance le test
python test_rag_retrieval.py
```

Le script va effectuer **3 tests** :
1. **TEST 1** : Recherche sémantique SANS filtre
2. **TEST 2** : Recherche sémantique AVEC filtre (rules only)
3. **TEST 3** : Recherche de texte EXACT dans tous les chunks

### Étape 2 : Analyse les résultats

#### Scénario A : TEST 3 trouve "Voleur sans" dans plusieurs chunks
✅ **Le texte est dans la base**
❌ **Mais la recherche sémantique ne le trouve pas**

**Cause** : Problème d'embeddings multilingues
**Solutions** :
1. Augmente `k_retrieval_encyclo` à 100 dans `config.yaml`
2. Essaye une requête plus directe : "Voleur sans mémoire" au lieu de "Parle-moi de..."
3. Réinitialise la base avec des chunks plus gros (chunk_size: 1200)

---

#### Scénario B : TEST 3 NE trouve PAS "Voleur sans"
❌ **Le texte N'EST PAS dans la base**

**Cause** : PDF manquant ou extraction échouée
**Solutions prioritaires** :

1. **Vérifie que le PDF existe** :
   ```bash
   # Liste les PDFs dans Data/
   dir Data\ /s *.pdf
   # ou
   ls -R Data/
   ```

2. **Vérifie le nom exact du PDF** :
   - Le PDF doit contenir les règles sur le Tarot des Ombres
   - Il doit être dans `Data/` ou `Data/Regles/`

3. **Vérifie l'extraction PDF** :
   Lance le script de test d'extraction :
   ```bash
   python test_pymupdf.py
   ```

4. **Réinitialise complètement la base** :
   ```bash
   # Ferme Streamlit (Ctrl+C)
   # Supprime la base
   rmdir /s /q lames_db     # Windows
   # ou
   rm -rf lames_db          # Linux/Mac

   # Relance l'app
   streamlit run app.py
   ```

---

#### Scénario C : TEST 1 et TEST 2 trouvent des chunks mais SANS le bon texte
⚠️ **La recherche sémantique renvoie des résultats mais ils ne contiennent pas l'info recherchée**

**Cause** : Les embeddings ne comprennent pas la requête
**Solutions** :
1. Formule la question différemment :
   - ✅ "Voleur sans mémoire"
   - ✅ "arcane 14 tarot"
   - ❌ "Parle-moi de l'arcane..."

2. Augmente drastiquement `k_retrieval_encyclo` :
   ```yaml
   k_retrieval_encyclo: 100
   ```

3. Active `disable_category_filter: true` pour chercher partout

---

## 🔧 Solutions rapides

### Solution 1 : Désactiver le filtre complètement

Dans `config.yaml` :
```yaml
rag:
  disable_category_filter: true
```

Puis relance l'app et reteste.

### Solution 2 : Augmenter massivement k

Dans `config.yaml` :
```yaml
rag:
  k_retrieval_encyclo: 100  # Au lieu de 50
```

### Solution 3 : Chunks plus gros

Dans `config.yaml` :
```yaml
rag:
  chunk_size: 1200   # Au lieu de 800
  chunk_overlap: 400 # Au lieu de 300
```

Puis **RÉINITIALISE** la base (supprime `lames_db/`).

### Solution 4 : Vérifier le PDF

1. Ouvre le PDF manuellement
2. Cherche "Voleur sans Mémoire" avec Ctrl+F
3. Si tu le trouves, note la page exacte
4. Vérifie que le texte n'est pas une IMAGE (auquel cas PyMuPDF ne peut pas l'extraire)

---

## 🎯 Actions immédiates

**Pour diagnostiquer rapidement** :

1. **Lance** : `python test_rag_retrieval.py`
2. **Regarde TEST 3** :
   - Si ✅ trouvé → Problème d'embeddings, augmente k à 100
   - Si ❌ non trouvé → PDF manquant ou extraction échouée

3. **Si TEST 3 = non trouvé** :
   - Vérifie que le PDF existe dans `Data/` ou `Data/Regles/`
   - Ouvre le PDF et cherche "Voleur sans Mémoire" manuellement
   - Si c'est une image, le texte n'est pas extractible
   - Si c'est du texte sélectionnable, réinitialise la base

4. **Si TEST 3 = trouvé** :
   - Augmente `k_retrieval_encyclo` à 100
   - Réinitialise la base avec `chunk_size: 1200`
   - Essaye "Voleur sans mémoire" (sans "Parle-moi de...")

---

## 📊 Vérification de la base

Pour vérifier que la base contient bien tes PDFs :

```bash
# Ouvre le fichier de métadonnées
type lames_db\corpus_metadata.json   # Windows
# ou
cat lames_db/corpus_metadata.json    # Linux/Mac
```

Tu devrais voir la liste de tous les PDFs indexés.

---

## 💡 Pourquoi NotebookLM fonctionne ?

NotebookLM utilise probablement :
1. **Chunking adaptatif** par sections/titres
2. **Embeddings multimodaux** plus puissants
3. **Recherche hybride** (sémantique + keyword)
4. **Reranking** des résultats

Notre système peut être amélioré mais nécessite du tuning pour ton corpus spécifique.

---

**Lance `python test_rag_retrieval.py` et envoie-moi les résultats du TEST 3** 🔍
