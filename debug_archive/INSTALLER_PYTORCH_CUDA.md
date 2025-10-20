# 🚀 Installation PyTorch 2.7 avec CUDA 12.8 pour RTX 5070 Ti

## 📋 Pourquoi cette mise à jour ?

Ta **RTX 5070 Ti** utilise l'architecture **Blackwell (sm_120)** qui nécessite :
- **CUDA 12.8** minimum
- **PyTorch 2.7+** (sorti en avril 2025)

Sans cela, les embeddings tournent sur **CPU** au lieu de **GPU** (beaucoup plus lent).

## ⚡ Bénéfices du GPU

| Opération | CPU | RTX 5070 Ti | Gain |
|-----------|-----|-------------|------|
| Génération embeddings | ~5 min | ~30 sec | **10x** plus rapide |
| Reconstruction base | 20 min | 2-3 min | **7x** plus rapide |

## 🔧 Installation

### Étape 1 : Désinstaller l'ancien PyTorch

```bash
# Active l'environnement virtuel
venv\Scripts\activate

# Désinstalle PyTorch actuel
pip uninstall torch torchvision torchaudio
```

### Étape 2 : Installer PyTorch 2.7 avec CUDA 12.8

**Visite** : https://pytorch.org/get-started/locally/

**Ou utilise directement** :

```bash
# Pour Windows avec CUDA 12.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

**Note** : Si CUDA 12.8 n'est pas disponible, utilise CUDA 12.6 :
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

### Étape 3 : Vérifier l'installation

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"Aucun\"}')"
```

**Résultat attendu** :
```
PyTorch: 2.7.0+cu128
CUDA disponible: True
GPU: NVIDIA GeForce RTX 5070 Ti
```

Si `CUDA disponible: False`, vérifie que :
1. Les drivers NVIDIA sont à jour
2. CUDA Toolkit 12.8 est installé
3. PyTorch a bien été installé avec l'index cu128

### Étape 4 : Activer le GPU dans config.yaml

**C'est déjà fait !** Le fichier `config.yaml` a été modifié :
```yaml
use_cuda: true  # ✅ ACTIVÉ
```

### Étape 5 : Reconstruire la base vectorielle avec GPU

```bash
# 1. Supprime l'ancienne base
rmdir /s /q lames_db

# 2. Relance l'app
streamlit run app.py
```

**Pendant la reconstruction**, tu devrais voir :
```
🧮 Génération des embeddings avec BAAI/bge-m3...
   (Cela peut prendre plusieurs minutes pour X vecteurs)
```

Avec le GPU, cette étape sera **beaucoup plus rapide** (30 sec au lieu de 5 min).

## 🔍 Vérifier que le GPU est utilisé

### Méthode 1 : Task Manager Windows

1. Ouvre le **Gestionnaire des tâches** (Ctrl+Shift+Esc)
2. Va dans l'onglet **Performances**
3. Sélectionne **GPU**
4. Lance la reconstruction de la base
5. Tu devrais voir l'utilisation GPU monter à **80-100%** pendant l'embedding

### Méthode 2 : nvidia-smi

```bash
# Dans un terminal séparé
nvidia-smi

# Ou en monitoring continu
nvidia-smi -l 1
```

**Pendant l'embedding**, tu verras :
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 5XX.XX       Driver Version: 5XX.XX       CUDA Version: 12.8   |
|-------------------------------+----------------------+----------------------+
| GPU  Name            TCC/WDDM | Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce ...  WDDM | 00000000:01:00.0 On  |                  N/A |
|-------------------------------+----------------------+----------------------+
| GPU-Util  Mem-Usage |
| 95%       8192MiB   |  ← GPU utilisé à 95%
+---------------------------+
```

## ⚠️ Dépannage

### Erreur : "CUDA out of memory"

Si tu as une erreur mémoire GPU :

**Solution 1** : Réduis le batch size des embeddings

Modifie `core/rag.py` pour traiter les embeddings par petits lots.

**Solution 2** : Réduis `chunk_size` dans config.yaml
```yaml
chunk_size: 600  # Au lieu de 800
```

### Erreur : "CUDA not available"

**Cause 1** : Drivers NVIDIA obsolètes
```bash
# Vérifie la version
nvidia-smi

# Télécharge les derniers drivers : https://www.nvidia.com/drivers
```

**Cause 2** : CUDA Toolkit manquant
- Télécharge CUDA 12.8 : https://developer.nvidia.com/cuda-downloads
- Installe et redémarre

**Cause 3** : PyTorch CPU installé par erreur
```bash
# Vérifie
python -c "import torch; print(torch.version.cuda)"

# Si None, réinstalle avec cu128
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

### PyTorch 2.7 pas encore disponible ?

Si PyTorch 2.7 avec CUDA 12.8 n'est pas encore publié :

**Option 1** : Utilise PyTorch 2.6 avec CUDA 12.6
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu126
```

**Option 2** : Compile PyTorch from source (avancé)
- Suit les instructions : https://github.com/pytorch/pytorch

**Option 3** : Reste en CPU temporairement
```yaml
use_cuda: false  # En attendant PyTorch 2.7
```

## 🎯 Checklist finale

- [ ] PyTorch 2.7+ installé
- [ ] `torch.cuda.is_available()` retourne `True`
- [ ] `config.yaml` : `use_cuda: true`
- [ ] Base vectorielle supprimée (`lames_db/`)
- [ ] Application relancée pour reconstruction
- [ ] GPU utilisé pendant l'embedding (vérifié dans Task Manager)

## 📊 Performances attendues

Avec RTX 5070 Ti et PyTorch 2.7 CUDA 12.8 :

| Tâche | CPU (i9) | RTX 5070 Ti | Gain |
|-------|----------|-------------|------|
| Embedding 1000 chunks | ~3 min | ~15 sec | 12x |
| Reconstruction base (9 PDFs) | 15-20 min | 2-3 min | 7x |
| Recherche sémantique | ~1 sec | ~0.1 sec | 10x |

---

**Une fois PyTorch 2.7 CUDA 12.8 installé, ton système sera optimal ! 🚀**
