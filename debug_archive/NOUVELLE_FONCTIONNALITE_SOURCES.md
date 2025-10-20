# 🎯 Nouvelle fonctionnalité : Filtrage des sources en mode Encyclopédique

## 📋 Problème résolu

Tu as identifié un problème de **cohérence des données** :
- Les informations dans les **règles** sont **détaillées et techniques**
- Les informations dans l'**univers** sont **générales et narratives**
- Mélanger les deux peut créer des réponses incohérentes ou trop générales

## ✨ Solution implémentée

Un **sélecteur de sources** a été ajouté au mode Encyclopédique avec **3 options** :

### 📖 Option 1 : Règles uniquement (détaillées)
**Quand l'utiliser** : Questions techniques sur le système de jeu
- Arcanes du Tarot des Ombres (valeurs, sortilèges, rituels)
- Mécaniques de combat
- Calculs de Points d'Essence (PE)
- Règles précises du jeu

**Catégories recherchées** : `rules` + `unknown`

**Exemple de question** :
```
"Parle-moi de l'arcane du Tarot des Ombres 'Le Voleur sans Mémoire'"
```

**Résultat attendu** :
- Symbole et signification précise
- VD (Valeurs de Dé), M (Modificateurs), C (Complications), MD (Modificateur de Dé)
- Sortilèges typiques avec exemples du manuel
- Rituels typiques avec calculs de PE détaillés
- Citations directes du livre de règles

---

### 🌍 Option 2 : Univers uniquement (générales + romans)
**Quand l'utiliser** : Questions sur le lore, l'histoire, les personnages
- Contexte narratif de l'univers
- Personnages historiques (Cardinal de Richelieu, etc.)
- Événements historiques dans le jeu
- Romans et histoires de l'univers

**Catégories recherchées** : `universe_book` + `novel`

**Exemple de question** :
```
"Qui est le Cardinal de Richelieu dans cet univers ?"
"Raconte-moi l'histoire des Lames du Cardinal"
```

**Résultat attendu** :
- Informations narratives et contextuelles
- Descriptions générales
- Extraits des livres d'univers et romans

---

### 📖🌍 Option 3 : Règles + Univers (recommandé, sans romans)
**Quand l'utiliser** : Questions nécessitant contexte technique ET narratif
- Comprendre comment la magie fonctionne (règles + lore)
- Découvrir un concept avec ses mécaniques ET son contexte
- Questions mixtes

**Catégories recherchées** : `rules` + `universe_book` + `unknown`
**Exclut** : `novel` (romans, pour éviter le bruit)

**Exemple de question** :
```
"Comment fonctionne la magie des Lames ?"
"Explique-moi le système d'Arcanes"
```

**Résultat attendu** :
- Explication technique (des règles)
- Contexte narratif (de l'univers)
- Vision complète du sujet

---

## 🎮 Comment utiliser

### Dans l'interface

1. **Lance l'application** : `streamlit run app.py`
2. **Sélectionne le mode** : "Encyclopédique" (colonne droite)
3. **Choisis la source** : Nouveau sélecteur sous "Sources de recherche"
   - 📖 Règles uniquement (détaillées)
   - 🌍 Univers uniquement (générales + romans)
   - 📖🌍 Règles + Univers (recommandé, sans romans)
4. **Pose ta question** dans la zone principale
5. **Optionnel** : Active le mode DEBUG pour voir quelles catégories sont récupérées

### En mode DEBUG

Le mode DEBUG affiche maintenant :
- 🎯 **Filtre actif** : Quel filtre de source est utilisé
- **Catégorie de chaque chunk** : Pour vérifier que les bonnes sources sont récupérées

## 📊 Impact sur les résultats

| Question | Sans filtre | Avec "Règles uniquement" | Avec "Univers uniquement" | Avec "Règles + Univers" |
|----------|------------|-------------------------|---------------------------|------------------------|
| Arcane du Tarot | ⚠️ Mix règles+univers | ✅ Détails techniques précis | ❌ Trop général | ✅ Technique + contexte |
| Cardinal de Richelieu | ⚠️ Mix | ❌ Pas de lore | ✅ Contexte narratif | ✅ Lore complet |
| Système de magie | ⚠️ Mix | ⚠️ Que technique | ⚠️ Que narratif | ✅ Complet et équilibré |

## 🔧 Catégorisation des documents

Le système catégorise automatiquement tes PDFs selon leur emplacement :

```
Data/
├── Regles/                  → category: "rules"
│   └── Manuel_Regles.pdf
├── Univers/
│   ├── Livre_Univers.pdf   → category: "universe_book"
│   └── Roman_1.pdf         → category: "novel"
├── Scenarii/               → category: "scenario"
│   └── Scenario_1.pdf
└── Autre.pdf               → category: "unknown"
```

**Note** : Les documents `"unknown"` sont inclus dans "Règles uniquement" et "Règles + Univers" par précaution.

## 🎯 Recommandations d'utilisation

### Pour questions sur les Arcanes du Tarot
✅ **Utilise "📖 Règles uniquement"**
- Tu obtiendras les valeurs exactes (VD, M, C, MD)
- Les sortilèges et rituels avec exemples
- Les calculs de PE précis

### Pour questions sur l'univers narratif
✅ **Utilise "🌍 Univers uniquement"**
- Tu obtiendras le contexte historique
- Les descriptions narratives
- Les extraits des romans si pertinents

### Pour questions générales ou mixtes
✅ **Utilise "📖🌍 Règles + Univers"** (recommandé)
- Combine le meilleur des deux mondes
- Exclut les romans pour éviter le bruit
- Donne une vision complète

## 🐛 Dépannage

### "0 chunks récupérés" même avec filtre
1. Vérifie que tes PDFs sont dans les bons dossiers (Data/Regles/, Data/Univers/)
2. Lance `python test_rag_retrieval.py` pour diagnostiquer
3. Réinitialise la base vectorielle si nécessaire

### Les catégories ne correspondent pas
1. Vérifie la structure de tes dossiers
2. Les noms de dossiers doivent être :
   - `Regles` ou `regles` ou contenir "règles"
   - `Univers` pour les livres d'univers
   - Les fichiers dans `Univers/` sont catégorisés selon leur nom
3. Réinitialise la base après avoir réorganisé les fichiers

### Le mode DEBUG montre des catégories incorrectes
- La base a été construite avec l'ancienne structure
- **Solution** : Réinitialise complètement la base vectorielle
  1. Ferme Streamlit (Ctrl+C)
  2. Supprime `lames_db/`
  3. Relance l'app (reconstruction automatique)

## 📈 Améliorations futures possibles

- [ ] Sauvegarder le choix de filtre par défaut
- [ ] Filtrage multi-sélection (ex: Règles + Romans)
- [ ] Catégories personnalisables dans config.yaml
- [ ] Poids différents selon la catégorie (prioriser rules sur universe)

---

**Bon jeu avec les nouvelles sources ciblées ! 🎯📚**
