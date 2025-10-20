# 🎯 Configuration du Re-Ranking

## Qu'est-ce que le re-ranking ?

Le re-ranking est une technique qui **améliore drastiquement** la qualité de la récupération de chunks :

1. **Récupération initiale** : Récupère 100 chunks avec la recherche vectorielle classique
2. **Re-ranking** : Un modèle spécialisé (cross-encoder) évalue chaque chunk et les trie par pertinence
3. **Sélection finale** : Ne garde que les 20-50 meilleurs chunks

**Gain estimé : +40-60% de précision sur les chunks récupérés**

## Installation

### Étape 1 : Installer sentence-transformers

Si tu n'as pas déjà sentence-transformers, installe-le :

```bash
pip install sentence-transformers
```

### Étape 2 : Télécharger le modèle de re-ranking

Au premier lancement avec re-ranking activé, le modèle sera téléchargé automatiquement (~500 MB).

Le modèle utilisé : **BAAI/bge-reranker-v2-m3**
- Multilingue (excellent pour le français)
- Rapide (~200ms pour 100 chunks sur GPU)
- État de l'art pour le re-ranking

### Étape 3 : Vérifier que CUDA fonctionne (optionnel mais recommandé)

Le re-ranking est **beaucoup plus rapide** sur GPU :

```python
import torch
print(torch.cuda.is_available())  # Devrait afficher True
```

Si False, le re-ranking fonctionnera quand même sur CPU (plus lent mais acceptable).

## Configuration

Dans `config.yaml`, le re-ranking est configuré ainsi :

```yaml
rag:
  # Re-ranking activé par défaut
  enable_reranking: true
  rerank_model: "BAAI/bge-reranker-v2-m3"
  k_initial_retrieval: 100  # Nombre de chunks à récupérer initialement
  k_final_after_rerank: 20  # Nombre final en mode MJ
  k_final_after_rerank_encyclo: 50  # Nombre final en mode encyclopédique
```

### Paramètres ajustables :

- **k_initial_retrieval** : Plus c'est élevé, plus on a de chances de trouver les bons chunks (mais plus lent)
  - Valeur recommandée : 50-150
  - Maximum pratique : 200

- **k_final_after_rerank** : ⚠️ **OBSOLÈTE** - Le nombre final de chunks est maintenant contrôlé par le **slider dans l'interface**
  - Mode MJ : Pas de slider (utilise k_retrieval par défaut : 20)
  - Mode Encyclopédique : Slider "Chunks à récupérer" (10-100, par défaut : 50)

## Désactiver le re-ranking

Si tu veux désactiver le re-ranking (par exemple si ton PC est trop lent) :

Dans `config.yaml` :
```yaml
rag:
  enable_reranking: false  # ← Changer à false
```

## Performance attendue

### Avec re-ranking :
- **Précision** : +40-60%
- **Vitesse** :
  - GPU (CUDA) : +200-500ms par requête
  - CPU : +1-3s par requête

### Sans re-ranking :
- **Précision** : Baseline
- **Vitesse** : Rapide (pas de surcoût)

## Diagnostic

### Le re-ranking fonctionne-t-il ?

Lance Streamlit et regarde les logs dans le terminal :

```
🔧 Chargement du re-ranker : BAAI/bge-reranker-v2-m3 sur cuda...
✅ Re-ranker chargé avec succès
```

Puis à chaque requête :
```
🎯 Re-ranking : 100 → 50 chunks (scores: [0.89, 0.76, 0.65]...)
```

### Problèmes courants

1. **"CrossEncoder non disponible"**
   → `pip install sentence-transformers`

2. **"Impossible de charger le re-ranker"**
   → Vérifie que tu as assez de RAM (le modèle fait ~500 MB)
   → Essaie avec `use_cuda: false` dans config.yaml

3. **Trop lent**
   → Active CUDA si tu as une GPU NVIDIA
   → Réduis `k_initial_retrieval` à 50
   → En dernier recours, désactive le re-ranking

## Modèles alternatifs

Tu peux essayer d'autres modèles de re-ranking :

```yaml
rerank_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Plus léger, anglais seulement
rerank_model: "BAAI/bge-reranker-base"  # Plus léger que v2-m3
rerank_model: "BAAI/bge-reranker-large"  # Plus précis mais plus lent
```

**Recommandé** : Garde `BAAI/bge-reranker-v2-m3` (meilleur compromis vitesse/qualité/français)
