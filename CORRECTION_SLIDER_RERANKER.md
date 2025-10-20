# Correction : Slider encyclopédique non utilisé par le reranker

## Problème identifié

L'utilisateur a remarqué que le **slider "Chunks à récupérer"** du mode encyclopédique était ignoré par le reranker.

### Comportement avant correction

1. **Interface** : Slider permettant de choisir 10-100 chunks (valeur par défaut : 50)
2. **Code** : Le reranker **ignorait complètement le slider** et utilisait des valeurs codées en dur :
   ```python
   if self.mode == "encyclo":
       k_final = self.config['rag'].get('k_final_after_rerank_encyclo', 50)
   else:
       k_final = self.config['rag'].get('k_final_after_rerank', 20)
   ```

3. **Résultat** : Peu importe la valeur du slider, le reranker retournait toujours 50 chunks en mode encyclo.

## Cause

Le `RerankedRetriever` ne recevait pas la valeur du slider `k` et lisait directement depuis `config.yaml`.

**Flux de données** :
```
Interface (slider: 30)
  → app.py: get_qa_chain(k=30)
    → vectordb.as_retriever(search_kwargs={"k": 30})
      → RAGChain.create_qa_chain(retriever avec k=30)
        → RerankedRetriever
          ❌ IGNORE retriever.k
          ❌ LIT config['rag']['k_final_after_rerank_encyclo'] = 50
          → Retourne 50 chunks au lieu de 30
```

## Solution implémentée

### 1. Ajout d'un attribut `k_final` au RerankedRetriever (core/rag.py:700)

```python
class RerankedRetriever(BaseRetriever):
    """Retriever avec re-ranking intégré qui hérite de BaseRetriever"""
    base_retriever: Any
    reranker: Any
    config: Dict[str, Any]
    mode: str
    query_text: str
    k_final: int  # ← NOUVEAU : Nombre final de chunks depuis slider
```

### 2. Récupération du k depuis le retriever (core/rag.py:693)

```python
# Récupérer le k du slider depuis le retriever
k_from_slider = retriever.search_kwargs.get('k', 50)
```

### 3. Passage de k_final au constructeur (core/rag.py:705, 759)

```python
def __init__(self, base_retriever, reranker, config, mode, query_text, k_final):
    super().__init__(
        base_retriever=base_retriever,
        reranker=reranker,
        config=config,
        mode=mode,
        query_text=query_text,
        k_final=k_final  # ← NOUVEAU
    )

# ...

retriever = RerankedRetriever(original_retriever, self.rerank_documents,
                               self.config, mode, query, k_from_slider)
```

### 4. Utilisation de k_final au lieu de la config (core/rag.py:753-755)

```python
# Re-ranking avec k_final depuis le slider de l'interface
print(f"🎯 Utilisation du slider : k_final = {self.k_final}")
reranked = self.reranker(query, docs, self.k_final)
return reranked
```

### 5. Mise à jour de la documentation (config.yaml:38-39)

```yaml
# Note: Le nombre final de chunks est maintenant contrôlé par le SLIDER dans l'interface
# (k_final_after_rerank et k_final_after_rerank_encyclo ne sont plus utilisés)
```

## Flux de données après correction

```
Interface (slider: 30)
  → app.py: get_qa_chain(k=30)
    → vectordb.as_retriever(search_kwargs={"k": 30})
      → RAGChain.create_qa_chain(retriever avec k=30)
        → k_from_slider = retriever.search_kwargs.get('k', 50)  # = 30
          → RerankedRetriever(..., k_final=30)
            ✅ Utilise self.k_final = 30
            → Retourne 30 chunks
```

## Vérification

### Dans les logs

Après cette correction, les logs afficheront :

```
🎯 Utilisation du slider : k_final = 30
🎯 Re-ranking : 100 → 30 chunks (scores: [...])
```

Au lieu de :

```
🎯 Re-ranking : 100 → 50 chunks (scores: [...])
```

### Dans l'interface

1. Mode Encyclopédique
2. Déplace le slider à **30 chunks**
3. Pose une question
4. Vérifie dans les logs : doit afficher `k_final = 30`
5. Vérifie dans "🔍 DEBUG: Contexte RAG" : doit afficher **30 chunks** et non 50

## Impact

- ✅ **Le slider fonctionne maintenant correctement**
- ✅ L'utilisateur a le contrôle total sur le nombre de chunks
- ✅ Permet d'optimiser vitesse vs qualité dynamiquement
- ✅ Plus besoin de modifier config.yaml pour changer k_final

## Paramètres obsolètes

Ces paramètres de config.yaml ne sont **plus utilisés** :
- `k_final_after_rerank` (mode MJ)
- `k_final_after_rerank_encyclo` (mode encyclopédique)

Ils peuvent être supprimés ou laissés pour référence.

## Fichiers modifiés

- `core/rag.py` (lignes 693, 700, 705, 753-755, 759)
  - Ajout attribut `k_final` à `RerankedRetriever`
  - Récupération de k depuis `retriever.search_kwargs`
  - Utilisation de `self.k_final` au lieu de lire config

- `config.yaml` (lignes 38-39)
  - Note explicative sur l'obsolescence des paramètres k_final

- `RERANKING_SETUP.md` (lignes 63-65)
  - Documentation mise à jour

## Date

2025-10-19
