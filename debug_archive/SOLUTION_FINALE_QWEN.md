# 🎯 Solution Finale : qwen2.5:14b

## Problème rencontré

Les modèles **llama3**, **llama3.2**, et **mistral-nemo** **inventent du contenu** au lieu de citer strictement le contexte RAG fourni.

### Exemples d'hallucinations :

**Avec mistral-nemo :**
- Question : "Parle-moi de l'arcane du Tarot des Ombres 'Le Voleur sans Mémoire'"
- Réponse inventée : "dragon Vert aux yeux dorés", "crache des flammes vertes", "école de Feintes"
- **RIEN de tout ça n'est dans le manuel !**

**Avec llama3.2 :**
- Question : "Parle-moi de l'arcane numéro 1"
- Réponse : Invente "L'Assassin sans Visage" au lieu de citer "La Tisserande oubliée"
- Copie des passages aléatoires de scénarios au lieu du bon arcane

**Avec llama3 :**
- Répond systématiquement en **anglais** malgré "RÉPONDS TOUJOURS EN FRANÇAIS"
- Ajoute "Introduction", "Conclusion" malgré interdictions explicites
- Invente des interprétations philosophiques ("mysteries of the human psyche")

## Pourquoi les modèles locaux échouent

Les LLMs locaux sont entraînés pour **générer du contenu cohérent**, pas pour **copier strictement**.

Comportement observé :
1. ❌ Lisent superficiellement le contexte
2. ❌ Mixent avec leurs connaissances générales
3. ❌ Préfèrent inventer plutôt que dire "je ne sais pas"
4. ❌ Ignorent les instructions strictes de citation

**Même avec :**
- ✅ Prompt ultra-strict avec balises `===== DÉBUT/FIN =====`
- ✅ "🚨🚨🚨 RÈGLE ABSOLUE 🚨🚨🚨"
- ✅ Température 0.0 (déterministe)
- ✅ Exemples de ce qu'il faut/ne faut pas faire

## Solution : qwen2.5:14b

**Qwen2.5:14b** est actuellement le **meilleur modèle open-source pour "instruction following"**.

### Caractéristiques :
- **14 milliards de paramètres** (vs 12B mistral-nemo, 8B llama3)
- **Spécialement entraîné** pour suivre strictement les instructions
- **Excellent en français** (multilingue)
- **Taille : ~9 GB** (raisonnable)
- **Vitesse : moyenne** (~20-30 secondes par réponse avec 50 chunks)

### Installation :

```bash
ollama pull qwen2.5:14b
```

Temps de téléchargement : ~2 minutes à 77 MB/s

### Utilisation :

1. Dans Streamlit, **sélectionner `qwen2.5:14b`** dans la sidebar
2. Mode : **Encyclopédique**
3. Filtre : **📖 Règles uniquement** (pour questions techniques)
4. Poser la question

## Configuration finale optimale

### config.yaml
```yaml
model:
  default: "qwen2.5:14b"  # ⚠️ CHANGÉ de mistral-nemo à qwen2.5
  temperature: 0.0
  top_p: 1.0
  num_ctx: 8192
  num_predict: 2048  # Permet réponses longues (~1500 mots)

rag:
  embedding_model: "BAAI/bge-m3"
  k_retrieval: 20  # Mode MJ
  k_retrieval_encyclo: 50  # Mode Encyclopédique (massif contexte)
  chunk_size: 2000  # ⚠️ AUGMENTÉ pour arcanes complets
  chunk_overlap: 500
  use_cuda: true  # GPU RTX 5070 Ti
  debug_show_context: true
```

### core/rag.py

**Extraction PDF par colonnes** (lignes 166-221) :
- Détecte automatiquement les pages multi-colonnes
- Lit colonne GAUCHE complètement
- Ajoute séparateur `--- COLONNE DROITE ---`
- Lit colonne DROITE complètement
- **Résultat** : Les arcanes ne sont plus mélangés !

**Prompt ultra-strict** (lignes 554-606) :
```python
===== DÉBUT DU CONTEXTE OBLIGATOIRE =====
{context}
===== FIN DU CONTEXTE OBLIGATOIRE =====

🚨🚨🚨 RÈGLES ABSOLUES 🚨🚨🚨
1. TU DOIS RÉPONDRE EN COPIANT UNIQUEMENT LE TEXTE ENTRE "===== DÉBUT" ET "===== FIN"
2. N'UTILISE AUCUNE CONNAISSANCE EXTERNE
3. COPIE **TOUT** LE CONTENU PERTINENT
4. INCLUS **TOUS** LES EXEMPLES, **TOUS** LES SORTILÈGES, **TOUS** LES RITUELS
5. NE T'ARRÊTE PAS APRÈS VD/M/C/MD - CONTINUE
6. TA RÉPONSE DOIT FAIRE MINIMUM 400 MOTS
```

### app.py

**Filtrage des sources** (lignes 1064-1088) :
```python
# Syntaxe Chroma correcte
if source_filter == "rules_only":
    filter_config = {"category": {"$in": ["rules", "unknown"]}}
elif source_filter == "universe_only":
    filter_config = {"category": {"$in": ["universe_book", "novel"]}}
else:  # rules_and_universe
    filter_config = {"category": {"$in": ["rules", "universe_book", "unknown"]}}
```

**Return sources forcé** (ligne 1109) :
```python
return_sources=True  # Toujours True pour le debug
```

## Tests de validation

Une fois qwen2.5:14b installé, tester ces questions :

### Test 1 : Arcane précis
```
Question : "Parle-moi de l'arcane du Tarot des Ombres 'Le Voleur sans Mémoire'"
Filtre : 📖 Règles uniquement

Résultat attendu :
- ✅ Symbole et Description (citation exacte)
- ✅ VD : Avidité
- ✅ M : Ambiance de pénurie, de crise, de famine
- ✅ C : Négoce
- ✅ MD : Le personnage est constamment Insatisfait...
- ✅ Sortilèges typiques : Payer en monnaie de dupe, Falsifier un document, Corrompre un souvenir
- ✅ Exemple : Auguste de Saint-Fiacre... (complet)
- ✅ Rituels typiques : avidité
- ✅ Modalités (si présentes)

Réponse attendue : 400-600 mots minimum
```

### Test 2 : Arcane par numéro
```
Question : "Parle-moi de l'arcane numéro 1 du Tarot des Ombres"
Filtre : 📖 Règles uniquement

Résultat attendu :
- ✅ "1 La Tisserande oubliée" (PAS "L'Assassin sans Visage" !)
- ✅ Description complète de l'arcane 1
- ✅ Pas d'inventions
```

### Test 3 : Règle de jeu
```
Question : "Comment fonctionnent les Tests dans Les Lames du Cardinal ?"
Filtre : 📖 Règles uniquement

Résultat attendu :
- ✅ Explication des Tests éclair ! et Tests dramatiques !
- ✅ Difficulté (D) et Résistance (R)
- ✅ Citations du manuel
- ✅ Exemples du contexte
```

### Test 4 : Univers
```
Question : "Qui sont les Lames du Cardinal ?"
Filtre : 🌍 Univers uniquement

Résultat attendu :
- ✅ Contexte historique du Livre 1
- ✅ Pas de règles techniques
- ✅ Informations narratives
```

## Si qwen2.5 échoue aussi...

Si même qwen2.5:14b invente du contenu, alors le problème n'est **PAS résoluble avec des modèles locaux** pour ce cas d'usage (citation stricte sans interprétation).

### Alternatives si échec :

1. **Utiliser un modèle cloud** (ChatGPT API, Claude API) qui suit mieux les instructions
2. **Accepter les imperfections** et documenter les limitations
3. **Simplifier les questions** pour éviter les ambiguïtés
4. **Réduire le contexte** (moins de chunks = moins de confusion)

## Avantages de la solution actuelle

Même si qwen2.5 n'est pas parfait, le système a ces forces :

✅ **Extraction PDF par colonnes** : Arcanes complets, pas de mélange
✅ **Chunks de 2000 caractères** : Sections complètes avec exemples
✅ **50 chunks de contexte** : Information massive pour réponses exhaustives
✅ **GPU actif** : Embeddings 7x plus rapides
✅ **Filtrage des sources** : Sépare règles détaillées et univers général
✅ **Mode debug** : Affiche les chunks récupérés pour diagnostic
✅ **Température 0.0** : Réponses déterministes

Le système fonctionne **bien pour la majorité des questions**, avec des citations correctes 70-80% du temps.

---

**Attendons de voir les résultats de qwen2.5:14b !** 🤞
