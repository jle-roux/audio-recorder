# Feature: Enregistreur Audio en Continu

## Feature Description
Cette fonctionnalité permet d'enregistrer en continu l'audio du PC dans un dossier dédié. L'enregistrement démarre automatiquement au lancement du programme et continue jusqu'à ce que l'utilisateur tape "exit" dans le terminal. Les fichiers audio sont sauvegardés dans le dossier `~/audio/` avec un système de nommage horodaté pour éviter les écrasements.

## User Story
En tant qu'utilisateur
Je veux enregistrer l'audio de mon PC en continu de manière simple
Afin de capturer des sessions audio sans intervention manuelle et les stopper proprement quand je le souhaite

## Problem Statement
Les utilisateurs ont besoin d'un moyen simple et fiable d'enregistrer l'audio de leur ordinateur en continu, avec un contrôle facile pour arrêter l'enregistrement. Les solutions existantes sont souvent complexes ou nécessitent des interfaces graphiques, alors qu'une solution en ligne de commande serait plus légère et automatisable.

## Solution Statement
Créer un programme Python simple qui utilise la bibliothèque PyAudio pour capturer l'audio du système en continu. Le programme enregistre dans des fichiers WAV horodatés dans `~/audio/` et écoute l'entrée utilisateur dans un thread séparé pour détecter la commande "exit" et arrêter proprement l'enregistrement.

## Relevant Files
Ce projet étant nouveau, tous les fichiers devront être créés.

### New Files

- **`src/audio_recorder.py`** - Module principal contenant la classe AudioRecorder pour gérer l'enregistrement audio
  - Gestion de l'initialisation de PyAudio
  - Capture du flux audio en continu
  - Sauvegarde dans des fichiers WAV horodatés
  - Gestion propre de l'arrêt

- **`src/main.py`** - Point d'entrée du programme
  - Initialisation du répertoire de sortie
  - Création et démarrage de l'enregistreur
  - Gestion de la boucle d'écoute de la commande "exit"
  - Gestion des signaux d'interruption (Ctrl+C)

- **`src/__init__.py`** - Fichier pour marquer le dossier comme package Python

- **`tests/test_audio_recorder.py`** - Tests unitaires pour AudioRecorder
  - Tests d'initialisation
  - Tests de création de fichiers
  - Tests de gestion des erreurs

- **`tests/__init__.py`** - Fichier pour marquer le dossier de tests comme package

- **`pyproject.toml`** - Configuration du projet avec uv
  - Définition des dépendances (PyAudio, wave)
  - Configuration du projet Python
  - Scripts d'exécution

- **`README.md`** - Documentation du projet
  - Description de la fonctionnalité
  - Instructions d'installation
  - Guide d'utilisation
  - Exemples

- **`.gitignore`** - Fichiers à ignorer par Git
  - Fichiers Python (__pycache__, *.pyc)
  - Environnements virtuels
  - Fichiers audio générés

## Implementation Plan

### Phase 1: Foundation
Mettre en place la structure du projet Python avec uv, créer les dossiers nécessaires, et configurer les dépendances. Initialiser le système de gestion des paquets et s'assurer que PyAudio peut être installé correctement sur le système.

### Phase 2: Core Implementation
Implémenter la classe AudioRecorder qui gère la capture audio via PyAudio, la création de fichiers WAV horodatés, et l'écriture continue des données audio. Implémenter également le système d'écoute de la commande "exit" dans un thread séparé pour permettre l'arrêt propre du programme.

### Phase 3: Integration
Créer le point d'entrée principal qui orchestre l'ensemble : création du dossier de destination, initialisation de l'enregistreur, gestion du cycle de vie du programme, et nettoyage propre des ressources. Ajouter la gestion des signaux système pour un arrêt gracieux.

## Step by Step Tasks

### 1. Initialisation du Projet
- Créer le fichier `pyproject.toml` avec la configuration uv
- Définir les dépendances du projet (PyAudio, pytest)
- Créer la structure de dossiers (src/, tests/)
- Initialiser les fichiers `__init__.py`

### 2. Création du Module AudioRecorder
- Créer `src/audio_recorder.py` avec la classe AudioRecorder
- Implémenter `__init__()` pour initialiser PyAudio et configurer les paramètres audio
- Implémenter `start_recording()` pour démarrer la capture audio
- Implémenter `stop_recording()` pour arrêter proprement l'enregistrement
- Implémenter `_generate_filename()` pour créer des noms de fichiers horodatés
- Implémenter `_record_audio()` pour la boucle d'enregistrement en continu
- Ajouter la gestion des erreurs et le nettoyage des ressources

### 3. Création du Point d'Entrée Principal
- Créer `src/main.py` avec la fonction main()
- Implémenter la création du dossier `~/audio/` s'il n'existe pas
- Implémenter la boucle d'écoute de la commande "exit"
- Ajouter la gestion des signaux (SIGINT, SIGTERM)
- Ajouter des messages informatifs pour l'utilisateur
- Implémenter le nettoyage propre à la sortie

### 4. Tests Unitaires pour AudioRecorder
- Créer `tests/test_audio_recorder.py`
- Tester l'initialisation de AudioRecorder
- Tester la génération de noms de fichiers
- Tester la création du répertoire de sortie
- Tester la gestion des erreurs (permissions, périphériques audio)
- Utiliser des mocks pour PyAudio

### 5. Documentation et Configuration
- Créer le `README.md` avec les instructions d'installation et d'utilisation
- Mettre à jour `.gitignore` pour exclure les fichiers audio et environnements virtuels
- Ajouter des exemples d'utilisation
- Documenter les dépendances système (PortAudio pour PyAudio)

### 6. Validation et Tests d'Intégration
- Installer les dépendances avec `uv sync`
- Exécuter les tests unitaires avec `uv run pytest`
- Tester le programme manuellement : lancer, enregistrer quelques secondes, taper "exit"
- Vérifier que les fichiers audio sont créés dans `~/audio/`
- Vérifier que les fichiers audio sont lisibles
- Tester l'interruption avec Ctrl+C
- Tester le comportement avec des permissions restreintes

## Testing Strategy

### Unit Tests
- **Test d'initialisation** : Vérifier que AudioRecorder s'initialise correctement avec les paramètres par défaut
- **Test de génération de noms** : Vérifier que les noms de fichiers suivent le format attendu (YYYY-MM-DD_HH-MM-SS.wav)
- **Test de création de dossier** : Vérifier que le dossier de sortie est créé s'il n'existe pas
- **Test de gestion d'erreurs** : Vérifier le comportement quand PyAudio n'est pas disponible ou échoue
- **Test de nettoyage** : Vérifier que les ressources sont libérées proprement

### Integration Tests
- **Test de bout en bout** : Lancer le programme, enregistrer pendant 5 secondes, envoyer "exit", vérifier qu'un fichier WAV valide existe
- **Test d'interruption** : Vérifier que Ctrl+C arrête proprement le programme et ferme le fichier audio
- **Test de permissions** : Vérifier le comportement quand le dossier de destination n'est pas accessible en écriture

### Edge Cases
- Aucun périphérique audio disponible sur le système
- Dossier `~/audio/` existant mais sans permissions d'écriture
- Disque plein pendant l'enregistrement
- Multiples lancements simultanés du programme
- Entrée utilisateur autre que "exit" (doit être ignorée)
- Fichier avec le même nom existe déjà (horodatage à la seconde devrait éviter cela)

## Acceptance Criteria
1. ✅ Le programme démarre sans erreur quand lancé depuis la ligne de commande
2. ✅ L'enregistrement audio commence immédiatement au lancement
3. ✅ Les fichiers audio sont sauvegardés dans `~/audio/` avec un nom horodaté
4. ✅ Taper "exit" dans le terminal arrête l'enregistrement et ferme le programme proprement
5. ✅ Le fichier audio généré est valide et lisible (format WAV)
6. ✅ Ctrl+C arrête également le programme proprement
7. ✅ Des messages clairs informent l'utilisateur du statut (démarrage, enregistrement, arrêt)
8. ✅ Tous les tests unitaires passent sans erreur
9. ✅ Le programme gère gracieusement les erreurs (permissions, matériel audio manquant)
10. ✅ La documentation explique clairement comment installer et utiliser le programme

## Validation Commands
Exécuter chaque commande pour valider que la fonctionnalité fonctionne correctement sans régression.

- `cd /home/julien/ai/audio-recorder && uv sync` - Installer toutes les dépendances
- `cd /home/julien/ai/audio-recorder && uv run pytest -v` - Exécuter tous les tests unitaires
- `cd /home/julien/ai/audio-recorder && uv run python -m src.main` - Tester le lancement du programme (arrêter manuellement avec exit)
- `ls -lh ~/audio/` - Vérifier que les fichiers audio ont été créés
- `file ~/audio/*.wav` - Vérifier que les fichiers sont bien au format WAV
- `cd /home/julien/ai/audio-recorder && uv run pytest --cov=src --cov-report=term-missing` - Vérifier la couverture de code

## Notes
### Dépendances Système
- **PortAudio** : PyAudio nécessite la bibliothèque PortAudio installée au niveau système
  - Ubuntu/Debian : `sudo apt-get install portaudio19-dev`
  - macOS : `brew install portaudio`
  - Fedora : `sudo dnf install portaudio-devel`

### Considérations Futures
- **Rotation des fichiers** : Limiter la taille totale des enregistrements pour éviter de remplir le disque
- **Formats audio** : Supporter d'autres formats (MP3, FLAC) pour réduire l'espace disque
- **Configuration** : Permettre de configurer le taux d'échantillonnage, les canaux, etc.
- **Segments temporels** : Créer un nouveau fichier toutes les X minutes pour faciliter la gestion
- **Interface CLI améliorée** : Utiliser argparse pour des options en ligne de commande
- **Indicateur visuel** : Afficher un indicateur de temps d'enregistrement ou de taille de fichier
- **Compression en temps réel** : Compresser les fichiers au fur et à mesure pour économiser l'espace
- **Détection de silence** : Ne pas enregistrer pendant les périodes de silence prolongé

### Architecture
Le programme utilise une architecture simple avec séparation des responsabilités :
- **AudioRecorder** : Responsable uniquement de la capture et sauvegarde audio
- **main** : Responsable de l'orchestration et de l'interface utilisateur
- Threading pour permettre l'écoute de la commande "exit" sans bloquer l'enregistrement
