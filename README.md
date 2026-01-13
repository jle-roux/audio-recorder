# Enregistreur Audio en Continu

Un programme Python simple et efficace pour enregistrer l'audio système de votre PC en continu. L'enregistrement capture le son de votre carte son (musique, vidéos, appels, etc.) au format MP3 compressé et se termine proprement lorsque vous tapez "exit" ou appuyez sur Ctrl+C.

## Fonctionnalités

- **Capture audio système** : Enregistre le son de la carte son (loopback) et non du microphone
- **Encodage MP3** : Fichiers compressés avec un bitrate de 128 kbps (économie d'espace ~90%)
- **Fichiers horodatés** : Sauvegarde automatique dans `~/audio/` avec horodatage (format: `YYYY-MM-DD_HH-MM-SS.mp3`)
- **Arrêt propre** : Tapez "exit" ou utilisez Ctrl+C pour terminer l'enregistrement
- **Détection automatique** : Trouve automatiquement le périphérique de loopback approprié
- **Gestion des erreurs** : Messages clairs en cas de problème (permissions, FFmpeg manquant, pas de loopback)

## Prérequis

### Dépendances système

Le programme nécessite **PortAudio** (pour PyAudio) et **FFmpeg** (pour l'encodage MP3) :

**Ubuntu/Debian :**
```bash
sudo apt-get install portaudio19-dev python3-dev ffmpeg
```

**macOS :**
```bash
brew install portaudio ffmpeg
```

**Fedora :**
```bash
sudo dnf install portaudio-devel ffmpeg
```

### Configuration audio système (Loopback)

Pour capturer le son système, vous avez besoin d'un périphérique loopback :

**Linux (PulseAudio) :**
La plupart des installations récentes de PulseAudio exposent déjà des périphériques Monitor. Vérifiez avec :
```bash
pactl list sources | grep -i monitor
```

Si aucun Monitor n'est disponible, chargez le module loopback :
```bash
pactl load-module module-loopback
```

Pour rendre cette configuration permanente, ajoutez à `/etc/pulse/default.pa` :
```
load-module module-loopback
```

**Windows :**
Activez "Stereo Mix" dans les paramètres audio de Windows (Panneau de configuration > Son > Onglet Enregistrement).

**macOS :**
Installez un outil de loopback comme [BlackHole](https://github.com/ExistentialAudio/BlackHole) ou Soundflower :
```bash
brew install blackhole-2ch
```

### Python

Python 3.8 ou supérieur est requis.

## Installation

1. **Cloner ou télécharger le projet** :
```bash
git clone https://github.com/jle-roux/audio-recorder.git
cd audio-recorder
```

2. **Installer les dépendances avec uv** :
```bash
uv sync
```

Cela installera automatiquement PyAudio, pydub et les dépendances de développement.

## Utilisation

### Lancer l'enregistrement

**Détection automatique (recommandé) :**
```bash
uv run python -m src.main
```

**Avec sélection manuelle du périphérique :**
```bash
# 1. Lister les périphériques disponibles
uv run python -m src.main --list-devices

# 2. Utiliser un périphérique spécifique
uv run python -m src.main --device 5
```

**Autres options :**
```bash
# Personnaliser le répertoire de sortie
uv run python -m src.main --output ~/mes-enregistrements

# Changer le bitrate MP3
uv run python -m src.main --bitrate 192k

# Combiner plusieurs options
uv run python -m src.main --device 5 --output ~/audio --bitrate 256k

# Afficher l'aide
uv run python -m src.main --help
```

Vous verrez un message de confirmation :
```
============================================================
ENREGISTREUR AUDIO EN CONTINU
============================================================

Répertoire de sortie: /home/julien/audio
Format d'encodage: MP3 (128 kbps)
Source audio: Détection automatique (loopback)

✓ Enregistrement démarré
✓ Fichier: 2025-10-10_14-30-45.mp3
✓ Périphérique: Monitor of Built-in Audio

Tapez 'exit' pour arrêter l'enregistrement, ou appuyez sur Ctrl+C
------------------------------------------------------------
```

### Lister les périphériques audio

Pour voir tous les périphériques audio disponibles et identifier le bon périphérique loopback :

```bash
uv run python -m src.main --list-devices
```

Cette commande affiche :
- Les périphériques Monitor PulseAudio/PipeWire détectés (Linux)
- Le Monitor par défaut recommandé ⭐
- Tous les périphériques PyAudio disponibles pour la capture
- Le périphérique qui serait utilisé par détection automatique
- Des suggestions de solutions si aucun périphérique loopback n'est trouvé

Exemple de sortie :
```
🔍 Détection PulseAudio/PipeWire
--------------------------------------------------------------------------------
✓ Monitor par défaut du système détecté:
  Monitor of Built-in Audio Analog Stereo
  → Mappé vers PyAudio index: 5 ⭐ RECOMMANDÉ

🎤 Tous les périphériques audio PyAudio disponibles pour capture:
--------------------------------------------------------------------------------
[5] Monitor of Built-in Audio Analog Stereo 🔊 [LOOPBACK]
    Canaux d'entrée: 2
    Taux d'échantillonnage: 44100 Hz

================================================================================
DÉTECTION AUTOMATIQUE
================================================================================
✓ Périphérique loopback détecté automatiquement:
  Index: 5
  Nom: Monitor of Built-in Audio Analog Stereo

💡 Pour utiliser ce périphérique:
   uv run python -m src.main
   # OU
   uv run python -m src.main --device 5
```

### Arrêter l'enregistrement

Deux méthodes :
1. **Tapez `exit` dans le terminal** et appuyez sur Entrée
2. **Appuyez sur `Ctrl+C`**

Le programme arrêtera proprement l'enregistrement et fermera le fichier audio.

### Localiser les fichiers

Les fichiers audio sont sauvegardés par défaut dans `~/audio/`.

Pour lister vos enregistrements :
```bash
ls -lh ~/audio/
```

Pour vérifier le format des fichiers :
```bash
file ~/audio/*.mp3
```

Pour analyser les propriétés audio d'un fichier :
```bash
ffprobe ~/audio/2025-10-10_14-30-45.mp3
```

## Configuration

### Options CLI

Le programme supporte les options suivantes en ligne de commande :

| Option | Description | Défaut |
|--------|-------------|--------|
| `--list-devices` | Afficher tous les périphériques disponibles et quitter | - |
| `--device INDEX` | Spécifier l'index du périphérique à utiliser | Détection automatique |
| `--output DIR` | Répertoire de sortie pour les fichiers | `~/audio/` |
| `--bitrate RATE` | Bitrate MP3 (ex: 128k, 192k, 256k, 320k) | `128k` |
| `--help` | Afficher l'aide | - |

### Paramètres par défaut

Par défaut, l'enregistrement utilise :
- **Source audio** : Détection automatique du loopback/monitor système
- **Format de sortie** : MP3 (128 kbps)
- **Taux d'échantillonnage** : 44100 Hz
- **Canaux** : 2 (stéréo)
- **Format d'échantillon** : 16-bit PCM
- **Répertoire de sortie** : `~/audio/`

Les paramètres avancés (taux d'échantillonnage, canaux, format) peuvent être modifiés dans `src/audio_recorder.py` si nécessaire.

## Développement

### Structure du projet

```
audio-recorder/
├── src/
│   ├── __init__.py
│   ├── audio_recorder.py      # Classe principale d'enregistrement
│   ├── audio_devices.py       # Détection des périphériques audio
│   ├── mp3_encoder.py         # Encodage MP3 en temps réel
│   └── main.py                # Point d'entrée du programme
├── tests/
│   ├── __init__.py
│   ├── test_audio_recorder.py # Tests unitaires AudioRecorder
│   ├── test_audio_devices.py  # Tests détection périphériques
│   └── test_mp3_encoder.py    # Tests encodage MP3
├── specs/
│   └── system-audio-capture-mp3.md  # Spécifications détaillées
├── pyproject.toml             # Configuration du projet
├── README.md                  # Ce fichier
└── .gitignore                # Fichiers à ignorer
```

### Exécuter les tests

```bash
# Tests unitaires
uv run pytest -v

# Tests avec couverture de code
uv run pytest --cov=src --cov-report=term-missing
```

### Lancer le programme en mode développement

```bash
uv run python -m src.main
```

## Dépannage

### Erreur "Aucun périphérique de capture système (loopback) trouvé"

**Cause** : Aucun périphérique loopback/monitor n'est configuré ou détectable sur le système.

**Solution rapide** :
```bash
# 1. Lister les périphériques disponibles
uv run python -m src.main --list-devices

# 2. Si un périphérique loopback est visible, spécifiez-le manuellement
uv run python -m src.main --device INDEX
```

**Solutions détaillées par plateforme** :

**Linux (PulseAudio/PipeWire)** :
```bash
# Vérifier que PulseAudio/PipeWire est actif
pactl info

# Lister les sources disponibles
pactl list sources short

# Vérifier les Monitors disponibles
pactl list sources | grep -i monitor

# Si aucun Monitor, redémarrer PulseAudio/PipeWire
systemctl --user restart pipewire pipewire-pulse
# OU
pulseaudio --kill && pulseaudio --start

# Créer un loopback virtuel temporaire
pactl load-module module-loopback
```

**Windows** :
- Panneau de configuration → Son → Onglet Enregistrement
- Clic droit → "Afficher les périphériques désactivés"
- Activer "Stereo Mix" ou "Mixage stéréo"

**macOS** :
```bash
# Installer BlackHole
brew install blackhole-2ch

# OU installer Soundflower
brew install soundflower
```

### Erreur "FFmpeg n'est pas installé"

**Cause** : FFmpeg n'est pas installé ou n'est pas dans le PATH.

**Solution** :
- **Ubuntu/Debian** : `sudo apt-get install ffmpeg`
- **macOS** : `brew install ffmpeg`
- **Fedora** : `sudo dnf install ffmpeg`

Vérifiez l'installation avec : `which ffmpeg`

### Erreur de permissions

**Cause** : Pas de droits d'écriture dans `~/audio/`

**Solution** :
```bash
mkdir -p ~/audio
chmod 755 ~/audio
```

### PyAudio ne s'installe pas

**Cause** : PortAudio manquant ou mauvaise version de Python

**Solution** :
1. Installez PortAudio (voir section Prérequis)
2. Vérifiez votre version de Python : `python --version`
3. Sur Ubuntu/Debian, installez aussi `python3-dev` : `sudo apt-get install python3-dev`

### Le fichier MP3 est vide ou corrompu

**Cause** : L'enregistrement a été interrompu de manière incorrecte ou FFmpeg a échoué.

**Solution** :
1. Assurez-vous de toujours arrêter l'enregistrement proprement (tapez "exit" ou Ctrl+C)
2. Vérifiez que FFmpeg fonctionne : `ffmpeg -version`
3. Vérifiez les logs pour voir si des erreurs sont apparues pendant l'encodage

## Licence

Ce projet est un exemple éducatif sans licence spécifique.

## Auteur

Développé avec l'assistance de Claude Code.
