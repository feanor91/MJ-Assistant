# Correction : Scénarios vs Règles dans les réponses encyclopédiques

## Problème identifié

Lors de la requête "info sur la tisserande oubliée" en mode encyclopédique :
- ✅ Le **bon chunk** (description de l'arcane) était récupéré en position #1 avec un score de 0.906
- ✅ Le **filtre ChromaDB** fonctionnait correctement (100 chunks catégorie "rules")
- ❌ Mais le **modèle répondait avec du contenu de SCÉNARIO** au lieu de la définition de l'arcane

### Exemple concret

**Chunks récupérés :**
1. **Chunk #1** : ✅ "La Tisserande oubliée est la représentation de la mère disparue..." (RÈGLE - arcane #1)
2. **Chunk #2** : ❌ "...la Sainte-Chapelle...l'évasion du duc de Beaufort..." (SCÉNARIO)
3. **Chunk #3** : ✅ "L'Astrologue en Prière..." (RÈGLE - arcane #0)

**Réponse donnée :** Parlait du vicomte d'Orvand et Marciac (scénario), ignorant le Chunk #1.

### Cause racine

1. **Le Livre 2 - Le Jeu.pdf** contient :
   - Les règles du jeu (pages 1-~200)
   - **2 scénarios complets** (pages ~200-256)

2. Comme tout le fichier est dans `Data/Regles/`, **TOUS les chunks sont catégorisés comme "rules"**, y compris les scénarios.

3. Le modèle (gpt-oss/mistral-nemo) se laissait **distraire par les chunks narratifs** malgré le bon chunk en position #1.

## Solutions implémentées

### 1. Prompt système amélioré (config.yaml:71-78)

Ajout d'instructions pour ignorer les scénarios :

```yaml
MÉTHODE DE TRAVAIL :
1. LIS le contexte fourni ci-dessous EN ENTIER
2. IDENTIFIE le chunk qui répond DIRECTEMENT à la question (souvent le Chunk #1)
3. IGNORE les passages narratifs, scénarios, ou histoires (personnages, lieux, événements)
4. PRIVILÉGIE les définitions, règles, statistiques, et descriptions techniques
5. CITE directement les passages pertinents (mot à mot)
6. ORGANISE ta réponse avec des titres markdown (## et ###)
7. Utilise des guillemets "" pour les citations directes
```

### 2. Instructions critiques dans le template (core/rag.py:625-632)

Ajout d'instructions **juste avant la réponse** du modèle :

```python
⚠️ INSTRUCTIONS CRITIQUES :
1. CHERCHE d'abord le chunk qui contient une DÉFINITION ou DESCRIPTION directe du sujet
2. IGNORE les passages narratifs (scénarios, histoires, dialogues, noms de personnages)
3. PRIVILÉGIE les chunks avec : VD, M, C, MD, Sortilèges, Rituels (= descriptions de règles)
4. Si le Chunk #1 répond directement à la question, utilise-le en priorité
5. Cite directement et complètement le texte pertinent
6. Organise ta réponse avec des titres markdown (## et ###)
7. Si aucun chunk ne contient de définition/règle, dis-le clairement
```

**Marqueurs de règles identifiés :**
- **VD** : Valeur Draconique (concept clé de l'arcane)
- **M** : Manifestation (effet visible)
- **C** : Compétence (compétence associée)
- **MD** : Marque Draconique (trait de personnalité)
- **Sortilèges typiques**
- **Rituels typiques**

Ces marqueurs sont **absents des scénarios** et signalent clairement une description de règle.

## Comment tester

1. Relance Streamlit
2. Mode **Encyclopédique**, filtre **"Règles uniquement"**
3. Pose la question : **"info sur la tisserande oubliée"**

### Résultat attendu

Le modèle devrait maintenant répondre avec le **Chunk #1** :

```
## 1 La Tisserande oubliée

"La Tisserande oubliée est la représentation de la mère disparue, celle qui tisse
les liens de la vie en offrant son sang pour sa progéniture. Elle symbolise aussi
le sacrifice, qui permit aux dragons de survivre durant les heures noires. Elle
constitue un arcane chargé de regret, symbole de la fertilité perdue des grands dragons."

**VD** : Sacrifice
**M** : Mouches et vermine
**C** : Médecine
**MD** : Le personnage est Dévoué et consacre une grande part de son temps à
s'occuper des autres, quitte à sacrifier son propre bien-être...

### Sortilèges typiques
- Soigner à distance
- Sacrifier son sang pour gagner de la force
- Bénir une naissance

### Rituels typiques
Exemple : Rituel du sang du guide...
```

Et **NON** parler du vicomte d'Orvand ou de Marciac.

## Vérification dans l'interface

Vérifie l'expander **"🔍 DEBUG: Contexte RAG"** :

- **Chunk #1** doit contenir "La Tisserande oubliée est la représentation..."
- **Chunks de scénario** (avec noms de personnages) devraient être ignorés dans la réponse
- Le modèle doit citer les **marqueurs** : VD, M, C, MD

## Limitations actuelles

**Cette correction ne résout PAS le problème de catégorisation** :
- Les scénarios dans le Livre 2 sont toujours catégorisés comme "rules"
- Le filtre ChromaDB ne peut pas les exclure
- Seul le **prompt du modèle** les ignore maintenant

**Solutions à long terme :**

1. **Extraction manuelle** : Extraire les 2 scénarios du Livre 2 dans des PDFs séparés et les placer dans `Data/Scenarii/`

2. **Détection automatique** : Améliorer le chunking pour détecter les sections (règles vs scénarios) dans un même PDF en analysant :
   - Présence de marqueurs (VD, M, C, MD, Sortilèges, Rituels) → règles
   - Présence de noms propres, dialogues, descriptions narratives → scénarios
   - Numéros de page (début vs fin du livre)

3. **Metadata enrichie** : Ajouter un champ `content_type` : "rule_definition", "scenario", "lore", etc.

## Fichiers modifiés

- `config.yaml` (lignes 71-78) : Instructions pour ignorer scénarios
- `core/rag.py` (lignes 625-632) : Instructions critiques dans le template
- `CORRECTION_FILTRE_ENCYCLO.md` : Documentation du filtre ChromaDB
- `CORRECTION_SCENARIO_VS_REGLES.md` : Ce document

Date : 2025-10-19
