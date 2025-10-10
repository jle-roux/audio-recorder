# Bug: Le son de la carte audio n'est pas enregistré

## Bug Description
Le programme ne parvient pas à enregistrer le son du système même si des périphériques Monitor sont détectés via PulseAudio/PipeWire. Le système détecte correctement les sources Monitor disponibles (MOMENTUM 4, Speaker + Headphones, HDMI outputs, etc.) mais le mapping entre PulseAudio et PyAudio échoue. Tous les moniteurs PulseAudio sont incorrectement mappés vers le périphérique PyAudio #12 ("pulse"), qui est une interface générique ne capturant pas directement l'audio système.

**Symptômes :**
- Le programme affiche "Aucun périphérique de capture système (loopback) trouvé"
- La commande `--list-devices` montre que 7 monitors PulseAudio sont détectés
- Tous les monitors sont mappés vers le même index PyAudio #12 ("pulse")
- Le périphérique "pulse" est une interface générique, pas un vrai monitor

**Comportement attendu :**
- Le programme doit détecter et utiliser automatiquement un monitor PulseAudio fonctionnel
- Le mapping entre PulseAudio et PyAudio doit trouver les vrais périphériques monitor dans PyAudio
- L'enregistrement doit capturer l'audio système en temps réel

## Problem Statement
Le mapping entre les sources PulseAudio/PipeWire et les périphériques PyAudio échoue car :

1. **Mapping incorrect** : La fonction `map_pulseaudio_to_pyaudio()` utilise une correspondance par nom qui mappe tous les monitors vers le périphérique générique "pulse" (index 12)

2. **Périphériques PyAudio limités** : PyAudio ne liste que les périphériques ALSA hardware (hw:0,0, hw:0,6, hw:0,7) et les plugins (pulse, pipewire, default, etc.), mais pas les monitors PulseAudio individuels

3. **Stratégie de détection inadaptée** : Le code actuel essaie de mapper par nom entre PulseAudio et PyAudio, mais PulseAudio expose les monitors avec des noms longs (`alsa_output.pci-0000_00_1f.3...monitor`) qui ne correspondent à aucun nom PyAudio

4. **Solution manquante** : PyAudio peut utiliser PulseAudio directement en spécifiant le nom du périphérique PulseAudio comme nom de périphérique, sans passer par l'index

## Solution Statement
Modifier la logique de détection et d'enregistrement pour utiliser directement les noms de périphériques PulseAudio au lieu de mapper vers des index PyAudio :

1. **Utiliser paAL SA directement** : PyAudio permet de spécifier un nom de périphérique ALSA/PulseAudio personnalisé lors de l'ouverture du stream via le paramètre `input_device_index` en utilisant un dictionnaire avec `"name"`

2. **Modifier la stratégie de détection** : Au lieu de chercher à mapper un nom PulseAudio vers un index PyAudio, conserver le nom PulseAudio complet et l'utiliser directement

3. **Simplifier l'ouverture du stream** : Utiliser `pyaudio.open()` avec le paramètre `as_loopback=True` pour PulseAudio ou spécifier directement le nom du périphérique monitor

4. **Améliorer la sélection automatique** : Prioriser les monitors non-HDMI et actifs (RUNNING) pour une meilleure expérience utilisateur

## Steps to Reproduce
1. Lancer le programme sans arguments : `uv run python -m src.main`
2. Observer l'erreur : "Aucun périphérique de capture système (loopback) trouvé"
3. Lister les périphériques : `uv run python -m src.main --list-devices`
4. Observer que tous les monitors PulseAudio sont mappés vers le même index #12 ("pulse")
5. Essayer manuellement : `uv run python -m src.main --device 12`
6. Constater que l'enregistrement démarre mais ne capture aucun son système

## Root Cause Analysis
**Cause principale** : PyAudio avec PulseAudio backend ne liste pas les périphériques Monitor individuels dans `get_device_count()` / `get_device_info_by_index()`. Il expose seulement des interfaces génériques comme "pulse", "pipewire", "default".

**Analyse détaillée** :
1. PulseAudio/PipeWire expose 7 sources monitor (vérifiable via `pactl list sources`)
2. PyAudio liste seulement les périphériques ALSA hardware (hw:0,0, hw:0,6, hw:0,7) et les plugins (pulse, pipewire, default)
3. La fonction `map_pulseaudio_to_pyaudio()` utilise une stratégie de correspondance par nom (exacte, partielle, par mot-clé)
4. Toutes les tentatives de correspondance échouent sauf le fallback final qui cherche "pulse" dans le nom et retourne toujours l'index 12
5. Le périphérique #12 ("pulse") est un proxy générique vers PulseAudio, mais sans spécifier le nom exact du monitor, il utilise la source par défaut (qui est un microphone, pas un monitor)

**Solution technique** :
PyAudio supporte la spécification de périphériques PulseAudio par leur nom complet en utilisant la variable d'environnement `PULSE_SOURCE` ou en configurant PulseAudio pour router correctement. Cependant, une meilleure approche est d'utiliser directement pulsectl pour enregistrer, ou de créer un périphérique virtuel PulseAudio qui combine tous les monitors.

**Approche retenue** :
Utiliser le périphérique "pulse" (index 12) mais configurer PulseAudio pour que sa source par défaut soit un monitor, ou utiliser `pactl` pour créer un module loopback temporaire avant l'enregistrement.

**Approche alternative (plus robuste)** :
Abandonner l'utilisation de PyAudio pour la capture et utiliser directement `parec` (PulseAudio record) ou la bibliothèque `sounddevice` qui a un meilleur support pour PulseAudio.

**Approche choisie pour ce fix** :
Modifier le code pour utiliser `sounddevice` au lieu de PyAudio, car sounddevice expose correctement les monitors PulseAudio et permet une sélection directe par nom ou index.

## Relevant Files
Utilisez ces fichiers pour corriger le bug :

- **src/audio_devices.py** (lignes 159-222, 224-323)
  - Contient les fonctions `map_pulseaudio_to_pyaudio()` et `find_loopback_device()`
  - Nécessite une refonte pour utiliser sounddevice au lieu de PyAudio
  - La logique de détection des monitors PulseAudio (lignes 101-156) fonctionne correctement et peut être conservée

- **src/audio_recorder.py** (lignes 1-246)
  - Contient la classe `AudioRecorder` qui utilise PyAudio pour l'enregistrement
  - Nécessite une refonte pour utiliser sounddevice à la place de PyAudio
  - Les lignes 102-152 gèrent l'ouverture du stream et doivent être adaptées
  - Les lignes 181-191 gèrent la lecture des frames audio et doivent être adaptées

- **src/mp3_encoder.py**
  - Doit être vérifié pour s'assurer de la compatibilité avec sounddevice
  - Probablement aucune modification nécessaire si l'interface reste identique (write_frames avec des bytes)

- **pyproject.toml**
  - Ajouter la dépendance `sounddevice` pour remplacer PyAudio
  - Conserver `pulsectl` pour la détection des monitors

### New Files
Aucun nouveau fichier nécessaire.

## Step by Step Tasks
IMPORTANT: Exécuter chaque étape dans l'ordre, de haut en bas.

### 1. Ajouter la dépendance sounddevice
- Exécuter `uv add sounddevice` pour ajouter la bibliothèque sounddevice au projet
- Vérifier que l'installation s'est bien passée

### 2. Mettre à jour audio_devices.py pour utiliser sounddevice
- Remplacer les imports PyAudio par sounddevice
- Modifier `list_audio_devices()` pour utiliser `sounddevice.query_devices()`
- Modifier `map_pulseaudio_to_pyaudio()` pour mapper vers les noms/index sounddevice (renommer en `map_pulseaudio_to_sounddevice()`)
- Mettre à jour `find_loopback_device()` pour retourner un nom ou index sounddevice compatible
- Adapter `get_device_info()` pour utiliser sounddevice
- Mettre à jour `print_available_devices()` pour afficher correctement les périphériques sounddevice

### 3. Mettre à jour audio_recorder.py pour utiliser sounddevice
- Remplacer les imports PyAudio par sounddevice
- Modifier le constructeur `__init__()` pour supprimer les paramètres spécifiques à PyAudio
- Réécrire `start_recording()` pour utiliser `sounddevice.InputStream` ou `sounddevice.RawInputStream`
- Adapter `_record_audio()` pour lire les données depuis sounddevice
- Mettre à jour `stop_recording()` et `_cleanup()` pour gérer correctement le stream sounddevice
- S'assurer que les données lues sont compatibles avec MP3Encoder

### 4. Vérifier la compatibilité avec mp3_encoder.py
- Lire le fichier mp3_encoder.py pour comprendre le format attendu
- S'assurer que les données de sounddevice sont dans le bon format (numpy array → bytes si nécessaire)
- Ajouter une conversion si nécessaire dans audio_recorder.py

### 5. Mettre à jour les tests unitaires
- Modifier `tests/test_audio_devices.py` pour tester avec sounddevice
- Modifier `tests/test_audio_recorder.py` pour mocker sounddevice au lieu de PyAudio
- S'assurer que tous les tests passent

### 6. Exécuter les tests et valider
- Exécuter `uv run pytest -v` pour vérifier que tous les tests passent
- Corriger les erreurs détectées

### 7. Tester manuellement la détection des périphériques
- Exécuter `uv run python -m src.main --list-devices`
- Vérifier que les monitors PulseAudio sont correctement listés avec leurs vrais noms
- Vérifier que le mapping vers sounddevice fonctionne correctement

### 8. Tester l'enregistrement automatique
- Lancer un son sur le système (musique, vidéo YouTube, etc.)
- Exécuter `uv run python -m src.main`
- Vérifier que l'enregistrement démarre sans erreur
- Laisser enregistrer pendant 10 secondes puis taper "exit"
- Vérifier que le fichier MP3 existe et contient bien le son du système

### 9. Tester l'enregistrement manuel avec périphérique spécifique
- Identifier un index de monitor via `--list-devices`
- Exécuter `uv run python -m src.main --device INDEX`
- Vérifier que l'enregistrement fonctionne avec le périphérique spécifié

### 10. Validation finale avec les commandes de validation
- Exécuter toutes les commandes listées dans la section "Validation Commands"
- S'assurer qu'il n'y a aucune régression

## Validation Commands
Exécuter chaque commande pour valider que le bug est corrigé avec zéro régression.

- `uv run pytest -v` - Exécuter tous les tests unitaires sans erreur
- `uv run python -m src.main --list-devices` - Afficher les périphériques et vérifier que les monitors sont correctement détectés
- `uv run python -m src.main` - Démarrer l'enregistrement automatique (doit détecter un monitor et démarrer sans erreur)
- Lancer une vidéo YouTube avec son, enregistrer 10 secondes, stopper avec "exit", puis vérifier avec `ffprobe ~/audio/*.mp3` que le fichier contient bien de l'audio
- `uv run python -m src.main --device INDEX` - Tester l'enregistrement avec un périphérique spécifique (INDEX à déterminer via --list-devices)
- `ls -lh ~/audio/` - Vérifier que les fichiers MP3 ont une taille raisonnable (> 100KB pour 10 secondes à 128kbps)
- `file ~/audio/*.mp3` - Vérifier que les fichiers sont bien au format MP3

## Notes
- **Pourquoi sounddevice plutôt que PyAudio** : sounddevice utilise PortAudio comme backend (comme PyAudio) mais expose mieux les périphériques PulseAudio/PipeWire. Il liste les monitors individuellement avec leurs vrais noms.

- **Compatibilité** : sounddevice est compatible avec pydub et FFmpeg, donc aucun changement n'est nécessaire au niveau de l'encodage MP3.

- **Migration douce** : sounddevice a une API plus simple que PyAudio. La migration devrait réduire le code et améliorer la maintenabilité.

- **Alternative considérée** : Utiliser directement `parec` (commande PulseAudio) via subprocess, mais cela introduirait une dépendance externe et compliquerait le code.

- **Installation système** : sounddevice nécessite libportaudio (déjà installé pour PyAudio), donc aucune nouvelle dépendance système.

- **Documentation à mettre à jour** : Le README.md mentionne PyAudio, il faudra le mettre à jour pour mentionner sounddevice (mais cela sort du scope de ce bug fix, ce sera fait dans une tâche séparée si nécessaire).
