# 🎨 Problème : Police décorative non extractible

## 🔍 Diagnostic

D'après l'image fournie, le texte "Le Voleur sans Mémoire" utilise une **police décorative stylisée** (type script/calligraphie).

Ce type de police peut poser problème pour l'extraction automatique.

## 🧪 Test d'extraction

Lance ce script pour vérifier si PyMuPDF arrive à extraire le texte :

```bash
python check_pdf_extraction.py
```

Ce script va :
1. Lister tous les PDFs dans `Data/`
2. Chercher "Voleur sans" dans chaque PDF
3. Afficher où le texte est trouvé (ou pas)
4. Tester des variantes ("Voleur", "mémoire", etc.)

## 📊 Résultats possibles

### Cas A : ✅ Texte trouvé avec PyMuPDF

```
✅ TROUVÉ à la page X
Contexte : ...Le Voleur sans Mémoire...
```

**Diagnostic** : L'extraction fonctionne !
**Cause du problème** : Le PDF n'a pas été lu ENTIÈREMENT (limite de 500 pages)
**Solution** : Déjà appliquée (`max_pdf_pages: null`)

**Action** : Réinitialise la base vectorielle
```bash
# 1. Ferme Streamlit
# 2. Supprime lames_db/
# 3. Relance l'app
```

---

### Cas B : ❌ Texte NON trouvé, mais variantes trouvées

```
❌ 'Voleur sans' NON TROUVÉ
✅ 'Voleur' trouvé (page Y)
✅ 'mémoire' trouvé (page Z)
```

**Diagnostic** : Les mots existent séparément mais pas ensemble
**Cause** : Le PDF a probablement des **sauts de ligne** ou **espaces** non standards dans la police décorative

**Solution** : Modifier la recherche pour être plus tolérante

Dans `core/rag.py`, l'extraction fonctionne mais le chunking peut casser le texte.

**Action** : Augmente `chunk_size` à 1500 et `chunk_overlap` à 500
```yaml
chunk_size: 1500
chunk_overlap: 500
```

Puis réinitialise la base.

---

### Cas C : ❌ AUCUN mot trouvé (ni "Voleur", ni "mémoire", ni "arcane")

```
❌ 'Voleur sans' NON TROUVÉ
❌ 'Voleur' NON trouvé
❌ 'mémoire' NON trouvé
❌ 'arcane' NON trouvé
```

**Diagnostic** : Le texte est une **IMAGE** ou utilise une **police vectorielle** non reconnue
**Cause** : PyMuPDF ne peut pas extraire les images de texte

**Solutions possibles** :

#### Solution 1 : OCR du PDF

Si le texte est une image, il faut utiliser un OCR :

```bash
# Installer tesseract OCR
# Puis utiliser pdf2image + pytesseract
pip install pytesseract pdf2image
```

Créer un script d'OCR pour ce PDF spécifique.

#### Solution 2 : Obtenir un PDF avec texte sélectionnable

- Demande au concepteur du jeu une version avec texte extractible
- Ou utilise un outil d'OCR externe (Adobe Acrobat, ABBYY FineReader)

#### Solution 3 : Extraction manuelle

Copie-colle manuellement les sections sur le Tarot des Ombres dans un fichier texte :

```
Data/Regles/Tarot_des_Ombres_Manuel.txt
```

Le système l'indexera automatiquement.

---

## 🎯 Solution immédiate recommandée

### Étape 1 : Vérifier si le texte est sélectionnable

1. Ouvre ton PDF dans un lecteur (Adobe, Foxit, etc.)
2. Essaye de **sélectionner** le texte "Le Voleur sans Mémoire"
3. Si tu peux le sélectionner → Le texte est extractible
4. Si tu ne peux PAS → C'est une image

### Étape 2 : Si le texte EST sélectionnable

**C'est bon signe !** PyMuPDF devrait pouvoir l'extraire.

**Actions** :
```bash
# 1. Lance le test
python check_pdf_extraction.py

# 2. Si trouvé : Réinitialise la base avec max_pdf_pages: null
# 3. Si non trouvé : Augmente chunk_size à 1500
```

### Étape 3 : Si le texte N'EST PAS sélectionnable

**Le PDF contient des images de texte.**

**Solutions** :
1. **OCR automatique** : Utilise un outil d'OCR sur le PDF
2. **Extraction manuelle** : Crée un fichier `.txt` avec les infos importantes
3. **Demande une autre version** : PDF avec texte sélectionnable

---

## 💡 Extraction manuelle (solution de secours)

Si rien ne fonctionne, crée ce fichier :

**`Data/Regles/Tarot_Ombres_Arcanes.txt`** :

```
2. Le Voleur sans Mémoire

Symbole chez les dragons de la soif insatiable de pouvoir,
de la volonté de régner sans partage, cet arcane représente
l'individualisme des dragons, qui délaissent le bien collectif
pour assouvir leur faim.

VD : Avidité.
M : Ambiance de pénurie, de crise, de famine.
C : Négoce.
MD : Le personnage est constamment Insatisfait...

[Copie-colle tout le reste depuis le PDF]
```

Puis :
```bash
# Réinitialise la base
rm -rf lames_db
streamlit run app.py
```

Le fichier `.txt` sera indexé et le système pourra répondre !

---

## 🔧 Vérification finale

Après avoir appliqué UNE des solutions :

```bash
# 1. Vérifie que le texte est dans la base
python test_rag_retrieval.py

# TEST 3 devrait afficher :
# ✅ Texte trouvé dans X chunks
```

Si ça fonctionne, teste dans l'interface :
- Mode : Encyclopédique
- Filtre : 📖 Règles uniquement
- Question : "Parle-moi du Voleur sans Mémoire"

**Tu devrais obtenir les informations complètes !** 🎉

---

**Lance `python check_pdf_extraction.py` et envoie-moi les résultats** 🔍
