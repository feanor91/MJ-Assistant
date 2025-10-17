# Exemples d'utilisation

Ce document présente des exemples concrets d'utilisation de l'Assistant MJ pour "Les Lames du Cardinal".

## Table des matières

- [Mode MJ Immersif](#mode-mj-immersif)
- [Mode Encyclopédique](#mode-encyclopédique)
- [Scénarios avancés](#scénarios-avancés)
- [Configuration personnalisée](#configuration-personnalisée)

---

## Mode MJ Immersif

### Exemple 1 : Démarrer une partie

**Entrée utilisateur :**
```
Je suis D'Artagnan, jeune gascon fraîchement arrivé à Paris. 
Je souhaite me rendre chez M. de Tréville, capitaine des mousquetaires du roi.
```

**Réponse du MJ (niveau "Longue narration immersive") :**
```
Le soleil de septembre brille sur les pavés parisiens alors que tu traverses 
la capitale à cheval. L'odeur caractéristique de la ville - mélange de pain 
frais et de crottin - emplit tes narines. La demeure de M. de Tréville se 
dresse devant toi, imposante, symbole du prestige des mousquetaires du roi.

Deux gardes surveillent l'entrée. L'un d'eux, un homme trapu à la moustache 
grisonnante, te toise d'un air méfiant.

OPTION 1 : T'approcher avec assurance et te présenter comme un gentilhomme 
de Gascogne venu voir M. de Tréville

OPTION 2 : Tenter d'impressionner les gardes en évoquant la lettre de 
recommandation de ton père

OPTION 3 : Rester humble et attendre poliment qu'on te donne la permission 
d'entrer

OPTION 4 : Observer les lieux et chercher une entrée alternative

[PNJ:Garde Moustache:Neutre]
[Lieu:Hôtel de Tréville:Non visité]
```

### Exemple 2 : Combat

**Entrée utilisateur :**
```
J'attaque l'espion du Cardinal avec mon épée !
```

**Réponse du MJ :**
```
Tu dégaines ton épée avec rapidité. La lame siffle dans l'air.

[Système de combat selon les règles]
Lance 2d6 + Escrime pour ton attaque.

L'espion tente d'esquiver (Difficulté: 9). S'il échoue, il subira des dégâts.

OPTION 1 : Viser une attaque puissante mais risquée (bonus de +2 aux dégâts, 
mais -1 à la défense au prochain tour)

OPTION 2 : Privilégier une attaque précise et calculée (pas de modificateur)

OPTION 3 : Feinter pour tromper sa garde (jet opposé d'Escrime, avantage si 
tu gagnes)

OPTION 4 : Tenter de désarmer plutôt que de blesser (Difficulté augmentée à 11)

[PNJ:Espion du Cardinal:Ennemi]
[Intrigue:Complot du Cardinal:En cours]
```

### Exemple 3 : Intrigue sociale

**Entrée utilisateur :**
```
Je tente de séduire la Reine pour obtenir des informations sur les ferrets.
```

**Réponse du MJ :**
```
Tu t'inclines respectueusement devant Anne d'Autriche. Son regard trahit à la 
fois l'inquiétude et une certaine curiosité envers ce jeune mousquetaire.

La situation est délicate. Selon les règles :
- Test de Courtoisie (Difficulté 10) pour ne pas offenser
- Si réussi, Test de Séduction ou Persuasion (Difficulté 12) pour gagner sa confiance

Les enjeux sont élevés. Un échec pourrait compromettre ta position à la cour.

OPTION 1 : User de charme et de compliments subtils (Séduction)

OPTION 2 : Faire appel à son sens de l'honneur et de la loyauté (Persuasion)

OPTION 3 : Mentionner discrètement que tu es au service du roi (Intimidation douce)

OPTION 4 : Prétendre avoir des informations qu'elle désire (Duperie)

[PNJ:Anne d'Autriche:Neutre]
[Lieu:Palais du Louvre:Visité]
[Intrigue:Affaire des ferrets:En cours]
```

---

## Mode Encyclopédique

### Exemple 1 : Règles de combat

**Question :**
```
Comment fonctionne le système de combat dans Les Lames du Cardinal ?
```

**Réponse :**
```
Selon le livre de règles, le système de combat fonctionne ainsi :

**Initiative** : Chaque participant lance 1d6 + bonus de Vivacité. 
L'ordre d'action va du plus haut au plus bas.

**Attaque** : Le joueur lance 2d6 + Compétence d'arme (Escrime, Armes à feu, etc.)
- Difficulté de base : 7 pour toucher
- Modificateurs selon la situation (couvert, mouvement, etc.)

**Défense** : La cible peut :
- Esquiver : 2d6 + Vivacité
- Parer : 2d6 + Escrime (armes de mêlée uniquement)

**Dégâts** : Si l'attaque réussit :
- Armes légères : 1d6 dégâts
- Armes moyennes : 2d6 dégâts  
- Armes lourdes : 3d6 dégâts

Les dégâts sont soustraits des Points de Vie. À 0 PV, le personnage est hors 
combat.

**Blessures critiques** : Sur un double 6 à l'attaque, le personnage inflige 
des dégâts maximaux + une blessure critique (table page 87).
```

### Exemple 2 : Création de personnage

**Question :**
```
Quelles sont les étapes pour créer un personnage ?
```

**Réponse :**
```
La création de personnage suit ces étapes :

1. **Concept** : Choisis l'origine et le métier de ton personnage parmi :
   - Gentilhomme, Mousquetaire, Soldat, Voleur, etc.

2. **Caractéristiques** : Répartis 12 points entre :
   - Force, Agilité, Vivacité, Résistance, Intelligence, Charisme

3. **Compétences** : Distribue 15 points dans les compétences :
   - Compétences de combat : Escrime, Armes à feu
   - Compétences sociales : Séduction, Persuasion, Intimidation
   - Compétences physiques : Athlétisme, Discrétion, Équitation
   - Autres compétences selon le background

4. **Talents** : Choisis 2 talents initiaux selon ta classe

5. **Équipement** : Achète ton équipement de départ (bourse de 100 livres)

6. **Background** : Définis l'histoire de ton personnage, ses motivations et 
   ses liens avec le monde.

**Points de Vie** : 10 + Résistance
**Points de Fortune** : 3 (permettent de relancer des dés)
```

### Exemple 3 : Règle spécifique

**Question :**
```
Comment fonctionnent les Points de Fortune ?
```

**Réponse :**
```
Les Points de Fortune représentent la chance et l'héroïsme du personnage.

**Utilisation** :
- Dépenser 1 Point de Fortune permet de :
  * Relancer un jet de dés (le sien ou celui d'un adversaire)
  * Transformer un échec en réussite partielle
  * Éviter une mort certaine (réduit à 1 PV au lieu de 0)
  * Déclarer un détail narratif mineur ("il y a une corde accrochée au mur")

**Récupération** :
- 1 point récupéré à chaque début de session
- 1 point pour une action particulièrement héroïque ou dramatique (décision du MJ)
- Maximum de 3 Points de Fortune simultanés

**Conseil** : Garde au moins 1 Point de Fortune pour les situations critiques !
```

---

## Scénarios avancés

### Gérer une partie multi-joueurs

**Structure de session :**

1. **Début de session**
```
Chargement de la dernière session : "Partie_Groupe_Session3"
```

2. **Tour par tour**
```
[Joueur 1 - Pierre] : Je surveille l'entrée
[Joueur 2 - Marie] : Je fouille la pièce
[Joueur 3 - Jacques] : J'écoute à la porte
```

3. **Sauvegarde**
```
Nom de session : "Partie_Groupe_Session4"
```

### Campagne longue

**Organisation recommandée :**

```
Sessions/
├── Prologue_Session1.json
├── Prologue_Session2.json
├── Acte1_Session3.json
├── Acte1_Session4.json
└── ...

Exports/
├── Prologue_Recapitulatif.md
├── Acte1_Recapitulatif.md
└── ...
```

### Combiner modes

**Workflow suggéré :**

1. **Préparation** (Mode Encyclopédique)
   - Chercher les règles de la prochaine scène
   - Vérifier les stats des PNJ
   - Consulter les lieux

2. **Jeu** (Mode MJ Immersif)
   - Narration immersive
   - Interaction avec les joueurs
   - Gestion de l'état du jeu

3. **Pause** (Mode Encyclopédique)
   - Clarifier une règle
   - Vérifier un détail de l'univers

---

## Configuration personnalisée

### Ajuster pour un groupe expérimenté

**config.yaml :**
```yaml
model:
  temperature: 0.2  # Plus de créativité
  
rag:
  k_retrieval: 8  # Plus de contexte
  
memory:
  max_mj_memory: 50  # Mémoire plus longue
```

### Optimiser pour solo

**config.yaml :**
```yaml
model:
  temperature: 0.0  # Plus de cohérence
  
memory:
  max_mj_memory: 20
  short_memory_context: 5  # Plus de contexte récent
```

### Partie rapide

**config.yaml :**
```yaml
rag:
  k_retrieval: 4  # Réponses plus rapides
  
ui:
  default_mode: "MJ immersif"
  auto_save_interval: 10  # Moins fréquent
```

### Mode "Oneshot"

**config.yaml :**
```yaml
memory:
  max_mj_memory: 15  # Session courte
  
ui:
  timeline_enabled: false  # Pas de timeline nécessaire
```

---

## Prompts personnalisés

### Modifier le style du MJ

**config.yaml :**
```yaml
prompts:
  mj_system: |
    Tu es un Maître de Jeu épique et théâtral des Lames du Cardinal.
    Utilise un style inspiré d'Alexandre Dumas : dramatique, avec du suspense
    et des descriptions riches. Intègre des phrases en ancien français quand 
    approprié.
    
    Réponds uniquement à partir du contexte fourni.
```

### Mode "Aide de jeu"

**config.yaml :**
```yaml
prompts:
  encyclo_system: |
    Tu es un assistant de règles concis et précis.
    Réponds de manière structurée avec :
    1. La règle principale
    2. Les exceptions
    3. Un exemple d'application
    
    Base-toi uniquement sur le contexte fourni.
```

---

## Conseils d'utilisation

### Pour le MJ

1. **Prépare ta session** : Utilise le mode Encyclopédique avant la partie
2. **Sauvegarde régulièrement** : Tous les 30-45 minutes
3. **Exporte en Markdown** : Crée des récapitulatifs entre sessions
4. **Utilise les niveaux de narration** : Adapte selon le rythme

### Pour les joueurs

1. **Sois spécifique** : Plus tu donnes de détails, mieux c'est
2. **Indique ton intention** : "Je veux convaincre le garde" plutôt que "Je parle au garde"
3. **Consulte ta fiche** : Garde-la ouverte dans le panneau de droite

### Techniques avancées

**Narration collaborative :**
```
[MJ propose 4 options]
[Joueur] : "Je choisis l'option 2, mais j'ajoute que je garde ma main sur 
mon épée en signe d'avertissement"
[MJ intègre le détail]
```

**Flashbacks :**
```
[Joueur] : "Je me souviens de ce que mon père m'a dit sur ce sujet"
[MJ utilise la mémoire pour créer une scène flashback cohérente]
```

---

## Ressources supplémentaires

- **Guide du MJ** : Consulte les PDFs officiels dans `Data/`
- **Fiches vierges** : Disponibles dans `Characters/templates/`
- **Scénarios pré-faits** : Télécharge depuis [lien communauté]

---

Bon jeu ! 🗡️⚔️