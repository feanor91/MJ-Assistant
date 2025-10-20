# ✅ SOLUTION TROUVÉE : Limite de pages PDF

## 🎯 Problème identifié

Le texte "Voleur sans Mémoire" est **à la fin du livre de règles**, mais la base vectorielle ne contient **que les 500 premières pages** !

**Cause** : `max_pdf_pages: 500` dans `config.yaml`

## 🔧 Solution appliquée

`config.yaml` ligne 107 :
```yaml
max_pdf_pages: null  # null = TOUT le PDF (plus de limite)
```

## ⚠️ ACTION REQUISE : Reconstruire la base vectorielle

**IMPORTANT** : La modification de `max_pdf_pages` ne prend effet qu'après reconstruction complète de la base.

### Étape 1 : Fermer Streamlit
```bash
# Dans le terminal où tourne Streamlit, appuie sur Ctrl+C
```

### Étape 2 : Supprimer la base existante
```bash
# Windows
rmdir /s /q lames_db

# Linux/Mac
rm -rf lames_db
```

### Étape 3 : Relancer l'application
```bash
streamlit run app.py
```

**Attends la reconstruction complète** (peut prendre 10-20 minutes pour un gros PDF).

Tu verras :
```
📄 Lecture des documents
📖 Fichier 1/X : MonPDF.pdf
...
⚙️ Création de la base vectorielle
✅ Base vectorielle prête !
```

### Étape 4 : Vérifier que tout est indexé
```bash
# Relance le test
python test_rag_retrieval.py
```

**TEST 3** devrait maintenant afficher :
```
✅ Texte trouvé dans X chunks
```

---

## 🧪 Test final

Une fois la base reconstruite :

1. **Mode** : Encyclopédique
2. **Filtre** : 📖 Règles uniquement
3. **Question** : "Parle-moi de l'arcane du Tarot des Ombres 'Le Voleur sans Mémoire'"

**Résultat attendu** :
- ✅ Citations directes du manuel
- ✅ VD, M, C, MD
- ✅ Sortilèges typiques avec exemples
- ✅ Rituels typiques avec calculs de PE
- ✅ Toutes les informations présentes dans le PDF

---

## 📊 Paramètres optimaux pour ton corpus

Après reconstruction, tu auras dans `config.yaml` :

```yaml
rag:
  k_retrieval_encyclo: 50  # Bon pour PDF complets
  chunk_size: 800
  chunk_overlap: 300

advanced:
  max_pdf_pages: null  # TOUT le PDF
```

Si ton PDF de règles est **très gros** (1000+ pages), tu peux :
- Garder `max_pdf_pages: null` (recommandé)
- OU augmenter à 1500-2000 au lieu de 500

---

## 💡 Pourquoi le problème est arrivé ?

1. Le paramètre `max_pdf_pages: 500` était une **sécurité** pour éviter les timeouts
2. Mais si ton livre de règles fait **600+ pages**, les dernières pages (dont le Tarot des Ombres) ne sont **jamais extraites**
3. La base vectorielle ne contenait donc **que le début du livre**
4. NotebookLM fonctionne car il lit **TOUT le PDF** sans limite

---

## 🎯 Checklist finale

- [ ] `config.yaml` modifié : `max_pdf_pages: null`
- [ ] Streamlit fermé (Ctrl+C)
- [ ] Dossier `lames_db/` supprimé
- [ ] Application relancée : `streamlit run app.py`
- [ ] Reconstruction terminée (10-20 min)
- [ ] Test validé : `python test_rag_retrieval.py`
- [ ] Interface testée avec question sur "Voleur sans Mémoire"

---

## 📝 Notes importantes

### Si la reconstruction est trop longue

Si ton PDF est **énorme** et la reconstruction prend trop de temps :

**Option 1** : Augmente `chunk_size` pour avoir moins de chunks
```yaml
chunk_size: 1200  # Au lieu de 800
```

**Option 2** : Limite à un nombre raisonnable de pages
```yaml
max_pdf_pages: 1500  # Assez pour capturer la fin
```

### Pour vérifier combien de pages a ton PDF

```python
import PyPDF2
with open("Data/Regles/ton_fichier.pdf", "rb") as f:
    reader = PyPDF2.PdfReader(f)
    print(f"Nombre de pages : {len(reader.pages)}")
```

---

**Une fois la reconstruction terminée, TOUT ton PDF sera indexé et le Voleur sans Mémoire sera enfin trouvé !** 🎉
