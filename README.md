# Enregistreur Audio en Continu

Un programme Python simple et efficace pour enregistrer l'audio de votre PC en continu. L'enregistrement démarre automatiquement au lancement et se termine proprement lorsque vous tapez "exit" ou appuyez sur Ctrl+C.

## Fonctionnalités

- **Enregistrement en continu** : Capture l'audio dès le lancement du programme
- **Fichiers horodatés** : Sauvegarde automatique dans `~/audio/` avec horodatage (format: `YYYY-MM-DD_HH-MM-SS.wav`)
- **Arrêt propre** : Tapez "exit" ou utilisez Ctrl+C pour terminer l'enregistrement
- **Format WAV** : Fichiers audio de qualité au format WAV standard
- **Gestion des erreurs** : Messages clairs en cas de problème (permissions, matériel audio)

## Prérequis

### Dépendances système

Le programme nécessite **PortAudio**, la bibliothèque sous-jacente à PyAudio :

**Ubuntu/Debian :**
```bash
sudo apt-get install portaudio19-dev python3-dev
```

**macOS :**
```bash
brew install portaudio
```

**Fedora :**
```bash
sudo dnf install portaudio-devel
```

### Python

Python 3.8 ou supérieur est requis.

## Installation

1. **Cloner ou télécharger le projet** :
```bash
cd /home/julien/ai/audio-recorder
```

2. **Installer les dépendances avec uv** :
```bash
uv sync
```

Cela installera automatiquement PyAudio et les dépendances de développement.

## Utilisation

### Lancer l'enregistrement

```bash
uv run python -m src.main
```

Vous verrez un message de confirmation :
```
============================================================
ENREGISTREUR AUDIO EN CONTINU
============================================================

Répertoire de sortie: /home/julien/audio

✓ Enregistrement démarré
✓ Fichier: 2025-10-10_14-30-45.wav

Tapez 'exit' pour arrêter l'enregistrement, ou appuyez sur Ctrl+C
------------------------------------------------------------
```

### Arrêter l'enregistrement

Deux méthodes :
1. **Tapez `exit` dans le terminal** et appuyez sur Entrée
2. **Appuyez sur `Ctrl+C`**

Le programme arrêtera proprement l'enregistrement et fermera le fichier audio.

### Localiser les fichiers

Les fichiers audio sont sauvegardés dans `~/audio/` (soit `/home/julien/audio/`).

Pour lister vos enregistrements :
```bash
ls -lh ~/audio/
```

Pour vérifier le format des fichiers :
```bash
file ~/audio/*.wav
```

## Configuration

Par défaut, l'enregistrement utilise :
- **Taux d'échantillonnage** : 44100 Hz
- **Canaux** : 2 (stéréo)
- **Format** : 16-bit PCM
- **Répertoire de sortie** : `~/audio/`

Ces paramètres peuvent être modifiés dans `src/audio_recorder.py` si nécessaire.

## Développement

### Structure du projet

```
audio-recorder/
├── src/
│   ├── __init__.py
│   ├── audio_recorder.py    # Classe principale d'enregistrement
│   └── main.py               # Point d'entrée du programme
├── tests/
│   ├── __init__.py
│   └── test_audio_recorder.py  # Tests unitaires
├── specs/
│   └── audio-recorder.md     # Spécifications détaillées
├── pyproject.toml            # Configuration du projet
├── README.md                 # Ce fichier
└── .gitignore               # Fichiers à ignorer
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

### Erreur "Périphérique audio non trouvé"

**Cause** : Aucun périphérique d'entrée audio n'est disponible ou PortAudio n'est pas installé.

**Solution** :
1. Vérifiez que PortAudio est installé (voir section Prérequis)
2. Vérifiez qu'un microphone est connecté et activé
3. Sur Linux, vérifiez les permissions ALSA/PulseAudio

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

## Améliorations futures

- **Rotation des fichiers** : Limiter l'espace disque utilisé
- **Formats audio supplémentaires** : Support MP3, FLAC pour réduire la taille
- **Configuration via CLI** : Options pour personnaliser taux d'échantillonnage, canaux, etc.
- **Segments temporels** : Créer un nouveau fichier toutes les X minutes
- **Détection de silence** : Ne pas enregistrer pendant les silences prolongés
- **Compression en temps réel** : Économiser l'espace disque
- **Indicateur de progression** : Afficher le temps d'enregistrement en direct

## Licence

Ce projet est un exemple éducatif sans licence spécifique.

## Auteur

Développé avec l'assistance de Claude Code.
