# ⚠️ RECONSTRUCTION DE LA BASE VECTORIELLE REQUISE

## Problème détecté
Le système hallucine car le **contexte RAG n'atteint pas correctement le modèle**.

## Cause
Les paramètres de chunking ont été modifiés :
- `chunk_size`: 600 → **800**
- `chunk_overlap`: 250 → **300**
- `k_retrieval_encyclo`: 30 → **50**

La base vectorielle existante utilise les anciens paramètres (chunks de 600).

## 🔧 Solution : RÉINITIALISER LA BASE

### Étape 1 : Réinitialiser dans l'interface
1. Lance l'application : `streamlit run app.py`
2. Dans la **colonne droite** (Configuration)
3. Section **"Base de données"**
4. Clique sur **"🗑️ Réinitialiser"**
5. Attends la reconstruction complète (peut prendre 5-10 minutes)

### Étape 2 : Alternative manuelle
Si le bouton ne fonctionne pas (fichiers verrouillés) :

1. **Ferme complètement Streamlit** (Ctrl+C dans le terminal)
2. **Supprime le dossier** `lames_db/` manuellement
3. **Relance l'application** : `streamlit run app.py`
4. La base sera reconstruite automatiquement avec les nouveaux paramètres

## 🔍 Vérification avec le mode DEBUG

Après reconstruction, teste avec :
```
Question : "Parle-moi de l'arcane du Tarot des ombres 'le Voleur sans mémoire'"
```

**Dans l'interface**, ouvre l'expander :
```
🔍 DEBUG: Contexte RAG complet envoyé au modèle (50 chunks)
```

**Vérifie** que les chunks contiennent le texte attendu :
- "Symbole chez les dragons de la soif insatiable de pouvoir"
- "VD : Avidité"
- "M : Ambiance de pénurie"
- "Sortilèges typiques : transactions, corruption, larcin"
- etc.

## 📊 Nouveaux paramètres optimisés

| Paramètre | Ancienne valeur | Nouvelle valeur | Impact |
|-----------|----------------|-----------------|--------|
| `chunk_size` | 600 | **800** | +33% de contexte par chunk |
| `chunk_overlap` | 250 | **300** | Meilleure continuité |
| `k_retrieval_encyclo` | 30 | **50** | +66% de chunks récupérés |
| Température | ≤0.3 | **0.0** | 100% déterministe |

**Total de texte au modèle** : 50 chunks × 800 caractères = **40,000 caractères** de contexte !

## 🎯 Résultat attendu

Avec ces paramètres, le modèle devrait :
- ✅ Trouver **l'information exacte** dans les 50 chunks
- ✅ **Citer fidèlement** grâce à température 0
- ✅ **Structurer** la réponse selon les 6 sections
- ❌ **NE PLUS halluciner** car le bon contexte arrive enfin

## 💡 Si le problème persiste

Si même après reconstruction le modèle hallucine :

### Option 1 : Vérifier que le PDF est bien indexé
```bash
# Vérifie que le PDF contenant "Le Voleur sans Mémoire" est dans Data/
ls Data/
```

### Option 2 : Vérifier les métadonnées de la base
Après reconstruction, le fichier `lames_db/corpus_metadata.json` doit exister et lister tous les PDFs.

### Option 3 : Utiliser le mode DEBUG
Ouvre le DEBUG et vérifie **manuellement** si le texte "Voleur sans Mémoire" apparaît dans les 50 chunks affichés.

**Si le texte n'apparaît pas** → Problème d'extraction PDF ou d'embeddings
**Si le texte apparaît** → Problème de prompt (renforcer encore plus)

### Option 4 : Augmenter encore k_retrieval_encyclo
Dans `config.yaml`, essaye :
```yaml
k_retrieval_encyclo: 80  # ou même 100
```

## 📝 Notes importantes

- Les embeddings multilingues (BAAI/bge-m3) devraient bien fonctionner pour le français
- Avec 50 chunks, il est **statistiquement très probable** que l'info soit trouvée
- La température 0 garantit que le modèle ne peut PAS improviser
- Le prompt ultra-strict force la citation

**Si tout est correctement configuré, le système DOIT citer fidèlement les sources.**
