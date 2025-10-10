# Bug: L'enregistreur capture uniquement le microphone au lieu de tous les sons système

## Bug Description
Le code actuel n'enregistre que le microphone et non tous les sons joués sur le PC (vidéos YouTube, réunions Google Meet, musique, etc.). Le programme recherche spécifiquement un périphérique "loopback" ou "monitor" via PyAudio et PulseAudio, mais échoue à trouver un périphérique approprié pour capturer l'audio système.

**Symptômes observés :**
- Le programme se termine avec l'erreur : "Aucun périphérique de capture système (loopback) trouvé"
- Les avertissements ALSA indiquent des problèmes de détection des périphériques
- Le README indique que le programme devrait capturer "le son de la carte son (loopback)" mais cela ne fonctionne pas

**Comportement attendu :**
- Le programme devrait capturer TOUS les sons joués par le système (YouTube, Google Meet, musique, etc.)
- L'enregistrement devrait fonctionner sans configuration PulseAudio complexe

**Comportement actuel :**
- Le programme recherche uniquement des périphériques "monitor" ou "loopback" spécifiques
- Si aucun périphérique n'est trouvé, le programme échoue complètement
- Aucune option de fallback vers le microphone par défaut ou d'autres sources

## Problem Statement
Le code dans `src/audio_devices.py` utilise une approche trop restrictive pour détecter les périphériques de capture système :

1. **Dépendance à PulseAudio Monitor** : Le code recherche spécifiquement des périphériques "Monitor" via `pulsectl`, qui ne sont pas toujours configurés ou disponibles
2. **Détection par mots-clés limitée** : Les mots-clés de fallback ("monitor", "stereo mix", "loopback") ne couvrent pas tous les cas d'usage Linux
3. **Pas de capture du "Default Source"** : Sur Linux avec PipeWire/PulseAudio, il faut utiliser le bon périphérique qui mixe toutes les sources audio

Le vrai problème est que sur un système Linux moderne avec PipeWire, il faut :
- Soit utiliser un périphérique "Monitor" d'un sink (sortie audio)
- Soit créer un loopback virtuel qui capture tout l'audio système
- Soit permettre à l'utilisateur de sélectionner manuellement le bon périphérique

## Solution Statement
Implémenter une approche multi-niveau pour détecter et utiliser les périphériques de capture système :

1. **Améliorer la détection PulseAudio/PipeWire** :
   - Détecter automatiquement le sink par défaut et utiliser son Monitor
   - Rechercher tous les Monitors disponibles, pas seulement certains types
   - Prioriser les Monitors non-HDMI mais accepter tous les Monitors si nécessaire

2. **Ajouter une option de configuration** :
   - Permettre à l'utilisateur de spécifier manuellement l'index du périphérique via CLI
   - Ajouter une commande pour lister tous les périphériques disponibles

3. **Améliorer le fallback** :
   - Si aucun Monitor n'est trouvé, proposer d'utiliser le périphérique par défaut
   - Afficher un avertissement clair mais continuer l'enregistrement

4. **Documentation et diagnostics** :
   - Améliorer les messages d'erreur pour guider l'utilisateur
   - Ajouter une commande de diagnostic qui liste TOUS les périphériques et leurs capacités

## Steps to Reproduce
1. Lancer le programme : `uv run python -m src.main`
2. Observer l'erreur : "Aucun périphérique de capture système (loopback) trouvé"
3. Le programme se termine sans enregistrer d'audio

**Pour vérifier les périphériques disponibles :**
```bash
# Lister les sources PulseAudio
pactl list sources

# Lister les périphériques PyAudio
uv run python -c "from src.audio_devices import print_available_devices; print_available_devices()"
```

## Root Cause Analysis

### Cause 1 : Détection trop restrictive des Monitors
Dans `src/audio_devices.py:46-77` (`get_pulseaudio_monitor_devices`), le code vérifie uniquement `source.monitor_of_sink is not None`. Cependant :
- Cette vérification peut ne pas couvrir tous les types de sources Monitor
- Sur certains systèmes, les Monitors peuvent avoir des propriétés différentes
- Le code ne tente pas de trouver le Monitor du sink par défaut

### Cause 2 : Mapping PulseAudio → PyAudio défaillant
Dans `src/audio_devices.py:80-106` (`map_pulseaudio_to_pyaudio`), la correspondance entre les noms PulseAudio et PyAudio est fragile :
- Les noms peuvent être très différents entre les deux APIs
- Le fallback vers "pulse" dans le nom est trop générique
- Aucun diagnostic pour comprendre pourquoi le mapping échoue

### Cause 3 : Pas de stratégie de fallback robuste
Dans `src/audio_devices.py:109-166` (`find_loopback_device`), si PulseAudio ne fonctionne pas :
- Le fallback par mots-clés est limité à des termes spécifiques
- Aucune tentative d'utiliser le périphérique d'entrée par défaut avec des paramètres appropriés
- Le code préfère échouer plutôt que d'essayer une alternative

### Cause 4 : Manque de flexibilité dans l'initialisation
Dans `src/audio_recorder.py:76-127` (`start_recording`), le code :
- Force `use_system_audio=True` par défaut
- Ne permet pas de spécifier manuellement un périphérique
- Échoue complètement si aucun loopback n'est trouvé

### Solution racine
La solution doit améliorer la détection des Monitors PulseAudio/PipeWire en :
1. Détectant le sink par défaut et utilisant son Monitor
2. Listant TOUS les Monitors disponibles et choisissant le meilleur
3. Permettant la sélection manuelle via un paramètre CLI
4. Fournissant des diagnostics clairs pour aider l'utilisateur

## Relevant Files
Fichiers à modifier pour corriger le bug :

### `src/audio_devices.py`
- **Ligne 46-77** : `get_pulseaudio_monitor_devices()` - Améliorer la détection des Monitors
- **Ligne 80-106** : `map_pulseaudio_to_pyaudio()` - Améliorer le mapping avec meilleure correspondance
- **Ligne 109-166** : `find_loopback_device()` - Ajouter détection du Monitor par défaut
- **Ligne 198-243** : `print_available_devices()` - Améliorer les diagnostics
- **Nouvelle fonction** : `find_default_sink_monitor()` - Trouver le Monitor du sink par défaut

### `src/audio_recorder.py`
- **Ligne 17-26** : `__init__()` - Ajouter paramètre `device_index` optionnel
- **Ligne 96-127** : `start_recording()` - Gérer le périphérique spécifié manuellement
- **Documentation** : Clarifier que le périphérique peut être spécifié

### `src/main.py`
- **Ligne 39-112** : `main()` - Ajouter argument CLI pour spécifier le périphérique
- **Nouvelle option** : `--list-devices` - Lister les périphériques disponibles
- **Nouvelle option** : `--device INDEX` - Spécifier manuellement le périphérique

### h3 New Files
Aucun nouveau fichier nécessaire. Les modifications se feront dans les fichiers existants.

## Step by Step Tasks

### Étape 1 : Améliorer la détection des Monitors PulseAudio/PipeWire
- Ajouter une fonction `find_default_sink_monitor()` dans `src/audio_devices.py` qui :
  - Détecte le sink par défaut via PulseAudio/PipeWire
  - Récupère le Monitor associé à ce sink
  - Retourne les informations du Monitor
- Modifier `get_pulseaudio_monitor_devices()` pour :
  - Lister TOUS les Monitors disponibles, pas seulement ceux avec `monitor_of_sink`
  - Inclure plus d'informations de diagnostic dans le retour
- Ajouter des logs de debug pour tracer la détection

### Étape 2 : Améliorer le mapping PulseAudio → PyAudio
- Modifier `map_pulseaudio_to_pyaudio()` pour :
  - Essayer plusieurs stratégies de correspondance (nom exact, nom partiel, description)
  - Logger les tentatives de correspondance pour faciliter le débogage
  - Retourner des informations supplémentaires (nom du périphérique trouvé)
- Tester la correspondance avec différents types de noms de périphériques

### Étape 3 : Refactoriser la détection des périphériques loopback
- Modifier `find_loopback_device()` pour :
  - Essayer d'abord `find_default_sink_monitor()` si PulseAudio est disponible
  - Ensuite essayer les Monitors listés par `get_pulseaudio_monitor_devices()`
  - En dernier recours, utiliser la recherche par mots-clés
  - Logger chaque étape de la détection pour faciliter le diagnostic
- Améliorer les messages d'erreur pour guider l'utilisateur vers la solution

### Étape 4 : Ajouter support de sélection manuelle du périphérique
- Modifier `AudioRecorder.__init__()` pour accepter un paramètre `device_index: Optional[int]`
- Modifier `AudioRecorder.start_recording()` pour :
  - Utiliser `device_index` si fourni au lieu de chercher automatiquement
  - Valider que le périphérique existe et peut capturer de l'audio
  - Afficher des informations claires sur le périphérique utilisé
- Documenter le nouveau paramètre dans les docstrings

### Étape 5 : Ajouter options CLI
- Ajouter argument `--list-devices` dans `src/main.py` :
  - Affiche tous les périphériques disponibles avec leurs index
  - Indique quel périphérique serait utilisé par défaut
  - Quitte après l'affichage
- Ajouter argument `--device INDEX` dans `src/main.py` :
  - Permet de spécifier manuellement l'index du périphérique
  - Passe l'index à `AudioRecorder`
  - Affiche un message d'erreur clair si l'index est invalide
- Utiliser `argparse` pour gérer les arguments CLI

### Étape 6 : Améliorer les diagnostics et messages
- Modifier `print_available_devices()` pour :
  - Afficher plus d'informations pour chaque périphérique (type, capacités)
  - Indiquer clairement quel périphérique serait utilisé par défaut
  - Suggérer des commandes pour résoudre les problèmes courants
- Améliorer les messages d'erreur dans tout le code :
  - Messages plus clairs et actionnables
  - Suggestions de solutions spécifiques au système détecté
  - Exemples de commandes à exécuter

### Étape 7 : Mettre à jour la documentation
- Mettre à jour `README.md` :
  - Documenter les nouvelles options CLI `--list-devices` et `--device`
  - Ajouter section de troubleshooting avec exemples concrets
  - Clarifier la différence entre capture système et capture microphone
- Mettre à jour les docstrings de toutes les fonctions modifiées

### Étape 8 : Exécuter les commandes de validation
- Exécuter TOUTES les commandes de validation listées ci-dessous
- Vérifier que chaque commande s'exécute sans erreur
- Corriger tout problème détecté avant de marquer le bug comme résolu

## Validation Commands
Exécuter chaque commande dans l'ordre pour valider avec 100% de confiance que le bug est corrigé :

### Validation de la détection des périphériques
```bash
# Lister les périphériques avec les nouvelles améliorations
uv run python -m src.main --list-devices

# Vérifier que le périphérique par défaut est détecté
uv run python -c "from src.audio_devices import find_loopback_device; print(f'Périphérique détecté: {find_loopback_device()}')"
```

### Validation de l'enregistrement par défaut
```bash
# Tester l'enregistrement avec détection automatique
# Lancer cette commande et jouer une vidéo YouTube pour vérifier la capture
uv run python -m src.main
# Taper 'exit' après 10 secondes
# Vérifier que le fichier MP3 existe et contient le son de la vidéo
ls -lh ~/audio/
ffprobe ~/audio/*.mp3
```

### Validation de la sélection manuelle
```bash
# Obtenir l'index d'un périphérique valide
DEVICE_INDEX=$(uv run python -c "from src.audio_devices import find_loopback_device; print(find_loopback_device())")

# Tester l'enregistrement avec sélection manuelle
uv run python -m src.main --device $DEVICE_INDEX
# Taper 'exit' après 10 secondes
# Vérifier que l'enregistrement fonctionne
```

### Validation des tests unitaires
```bash
# Exécuter tous les tests
cd /home/julien/ai/audio-recorder && uv run pytest -v

# Vérifier la couverture de code
uv run pytest --cov=src --cov-report=term-missing
```

### Validation de la régression
```bash
# Vérifier que le mode microphone fonctionne toujours
# (Modifier temporairement main.py pour use_system_audio=False)
# Vérifier que les fichiers MP3 sont bien créés et encodés
# Vérifier qu'aucune erreur n'apparaît pendant l'encodage
```

## Notes

### Dépendances
Le projet utilise déjà `pulsectl` (visible dans `pyproject.toml` normalement). Si ce n'est pas le cas, il faudra l'ajouter :
```bash
uv add pulsectl
```

### PulseAudio vs PipeWire
Sur les systèmes Linux modernes, PipeWire remplace souvent PulseAudio, mais PipeWire fournit une API compatible PulseAudio. La bibliothèque `pulsectl` fonctionne donc avec les deux.

### Fallback pour les systèmes sans PulseAudio
Si `pulsectl` n'est pas disponible ou si PulseAudio/PipeWire n'est pas en cours d'exécution, le code doit toujours fonctionner avec la détection par mots-clés de PyAudio.

### Configuration système requise
Pour capturer l'audio système sur Linux, l'utilisateur peut avoir besoin de :
1. Vérifier que PulseAudio/PipeWire est en cours d'exécution : `pactl info`
2. Lister les sources disponibles : `pactl list sources short`
3. Si aucun Monitor n'est disponible, créer un loopback virtuel :
   ```bash
   pactl load-module module-loopback
   ```

### Approche minimaliste
Cette solution reste chirurgicale et ne modifie que ce qui est nécessaire :
- Amélioration de la détection existante (pas de réécriture complète)
- Ajout d'options CLI sans changer le comportement par défaut
- Amélioration des messages sans modifier l'architecture
- Tests pour garantir zéro régression
