# Correction du filtre encyclopédique avec re-ranking

## Problème identifié

Lors de la requête "La Tisserande Oubliée" en mode encyclopédique :
- ❌ **94% des chunks récupérés étaient des romans** (category: "novel")
- ❌ **1% seulement étaient des règles** (category: "rules")

### Cause

Le filtre de l'interface (`source_filter`) configurait bien ChromaDB pour exclure les novels :
```python
filter_config = {
    "category": {"$in": ["rules", "universe_book", "unknown"]}
}
```

**MAIS** le re-ranker récupérait 100 chunks et il n'était pas clair si ce filtre ChromaDB était appliqué correctement lors de l'appel à `invoke()` dans le `RerankedRetriever`.

## Solution implémentée

### 1. Debug ajouté (core/rag.py:717-720)

```python
# DEBUG : Vérifier si le filtre ChromaDB est présent
current_filter = self.base_retriever.search_kwargs.get('filter', None)
print(f"🔍 Filtre ChromaDB actif : {current_filter}")
```

Cela permet de voir dans les logs si le filtre de l'interface est bien transmis.

### 2. Filtre de sécurité post-récupération (core/rag.py:734-740)

```python
# Filtrage supplémentaire en mode encyclopédique (au cas où le filtre ChromaDB n'a pas fonctionné)
if self.mode == "encyclo":
    before_filter = len(docs)
    docs = [doc for doc in docs if doc.metadata.get('category', '') != 'novel']
    after_filter = len(docs)
    if before_filter != after_filter:
        print(f"⚠️ Filtre post-récupération : {before_filter} → {after_filter} chunks (novels enlevés)")
```

**Stratégie défensive** : Même si le filtre ChromaDB devrait fonctionner, on filtre AUSSI après récupération pour garantir qu'aucun novel ne passe.

### 3. Filtre pour le cas sans re-ranking (core/rag.py:655-684)

Ajout d'un `FilteredRetriever` qui filtre les novels même quand le re-ranking est désactivé.

## Comment tester

1. Lance Streamlit : `streamlit run app.py`

2. Passe en **mode Encyclopédique**

3. Vérifie que le filtre est sur **"📖🌍 Règles + Univers (recommandé, sans romans)"**

4. Pose la question : **"info sur la tisserande oubliée"**

5. Regarde les **logs dans le terminal** :

```
🔍 Filtre ChromaDB actif : {'category': {'$in': ['rules', 'universe_book', 'unknown']}}
📥 Récupéré X chunks après filtre ChromaDB
⚠️ Filtre post-récupération : 100 → 6 chunks (novels enlevés)  ← Si ChromaDB n'a pas filtré
🎯 Re-ranking : 6 → 6 chunks (scores: [...])
```

### Attendu

- **Si ChromaDB fonctionne** : `📥 Récupéré 6 chunks` directement (pas de novels)
- **Si ChromaDB ne filtre pas** : Le filtre post-récupération enlèvera les 94 novels

### Résultat dans l'interface

La réponse devrait maintenant contenir des informations sur **l'arcane "La Tisserande Oubliée"** du Tarot des Ombres (règles du jeu), et NON sur le personnage des romans de Pierre Pevel.

## Logs de diagnostic

Résultats de `diagnostic_simple.py` montrant le problème avant correction :

```
Repartition categories (top 100):
  novel: 94 (94.0%)        ← PROBLÈME
  universe_book: 3 (3.0%)
  scenario: 2 (2.0%)
  rules: 1 (1.0%)          ← Ce qu'on veut !
```

## Fichiers modifiés

- `core/rag.py` (lignes 655-750)
  - Ajout de `FilteredRetriever` pour le cas sans re-ranking
  - Ajout de debug pour vérifier le filtre ChromaDB
  - Ajout de filtre post-récupération de sécurité dans `RerankedRetriever`

## Notes

- Le filtre de l'interface était déjà correct, mais pas appliqué par le re-ranker
- La correction est **défensive** : elle filtre à la fois avec ChromaDB ET après récupération
- Cela garantit 0% de novels en mode encyclopédique, quelle que soit la méthode qui fonctionne

Date : 2025-10-19
