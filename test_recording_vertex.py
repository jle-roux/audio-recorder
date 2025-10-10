#!/usr/bin/env python3
"""Script de test pour enregistrer de l'audio et extraire les paroles avec Vertex AI."""

import os
import time
import signal
import sys
from pathlib import Path

from src.audio_recorder import AudioRecorder
from google.cloud import speech


def signal_handler(signum, frame):
    """Gestionnaire de signaux pour un arrêt propre."""
    print("\n\nInterruption détectée. Arrêt de l'enregistrement...")
    sys.exit(0)


def transcribe_audio_with_vertex(audio_file_path: Path) -> str:
    """
    Transcrit un fichier audio en texte en utilisant Google Cloud Speech-to-Text API.

    Args:
        audio_file_path: Chemin vers le fichier audio à transcrire

    Returns:
        Texte transcrit
    """
    # Initialiser le client Speech-to-Text
    client = speech.SpeechClient()

    # Charger le fichier audio
    with open(audio_file_path, "rb") as audio_file:
        content = audio_file.read()

    # Configurer la requête de transcription
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        sample_rate_hertz=44100,  # Correspond au taux d'échantillonnage du recorder
        language_code="fr-FR",  # Langue française
        enable_automatic_punctuation=True,  # Ajouter la ponctuation automatiquement
        model="default",  # Modèle par défaut
    )

    # Effectuer la transcription
    print("Envoi de la requête à l'API Speech-to-Text...")
    response = client.recognize(config=config, audio=audio)

    # Extraire et combiner tous les résultats
    transcription = ""
    for result in response.results:
        transcription += result.alternatives[0].transcript + " "

    return transcription.strip()


def main():
    """Fonction principale pour tester l'enregistrement avec Vertex AI."""
    # Configurer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("TEST ENREGISTREMENT AUDIO + VERTEX AI")
    print("=" * 60)
    print()

    # Configurer la variable d'environnement pour utiliser le bon monitor
    os.environ['PULSE_SOURCE'] = 'bluez_output.80_C3_BA_0E_F4_09.1.monitor'

    # Créer l'enregistreur audio
    output_dir = Path.home() / "audio" / "enregistrements"
    recorder = AudioRecorder(
        output_dir=str(output_dir),
        bitrate='128k',
    )

    print(f"Répertoire de sortie: {output_dir}")
    print(f"Format d'encodage: MP3 (128k)")
    print(f"Durée: 10 secondes")
    print()

    try:
        # Démarrer l'enregistrement
        output_file = recorder.start_recording()
        print(f"✓ Enregistrement démarré")
        print(f"✓ Fichier: {output_file.name}")
        if recorder.device_name:
            print(f"✓ Périphérique: {recorder.device_name}")
        print()
        print("Enregistrement en cours...")

        # Enregistrer pendant 10 secondes
        for i in range(10, 0, -1):
            print(f"  {i} secondes restantes...", end='\r')
            time.sleep(1)

        print("\n")
        print("Arrêt de l'enregistrement et encodage MP3 en cours...")
        recorder.stop_recording()
        print("✓ Enregistrement terminé et encodé en MP3")
        print(f"✓ Fichier disponible: {output_file}")
        print()

        # Vérifier que le fichier existe et a une taille raisonnable
        if output_file.exists():
            file_size = output_file.stat().st_size
            print(f"✓ Fichier créé avec succès ({file_size / 1024:.1f} KB)")

            if file_size < 10000:  # Moins de 10 KB est suspect
                print("⚠ ATTENTION: Le fichier semble très petit, il pourrait être vide ou corrompu")
            else:
                print("✓ Taille du fichier semble correcte")
                print()

                # Extraction des paroles avec Vertex AI
                print("=" * 60)
                print("EXTRACTION DES PAROLES AVEC VERTEX AI")
                print("=" * 60)
                print()

                try:
                    transcription = transcribe_audio_with_vertex(output_file)

                    if transcription:
                        print("✓ Transcription réussie !")
                        print()
                        print("PAROLES EXTRAITES:")
                        print("-" * 60)
                        print(transcription)
                        print("-" * 60)
                    else:
                        print("⚠ Aucune parole détectée dans l'enregistrement")
                        print("Cela peut arriver si:")
                        print("- Aucun son n'était joué pendant l'enregistrement")
                        print("- Le volume était trop faible")
                        print("- L'audio ne contenait pas de parole (musique instrumentale, etc.)")
                except Exception as e:
                    print(f"✗ Erreur lors de la transcription: {e}")
                    print()
                    print("Vérifiez que:")
                    print("1. Les credentials GCP sont configurés (GOOGLE_APPLICATION_CREDENTIALS)")
                    print("2. L'API Speech-to-Text est activée dans votre projet GCP")
                    print("3. Vous avez les permissions nécessaires")
        else:
            print("✗ ERREUR: Le fichier n'a pas été créé")
            return 1

    except Exception as e:
        print(f"✗ Erreur: {e}", file=sys.stderr)
        recorder.stop_recording()
        return 1

    finally:
        print()
        print("=" * 60)
        print("TEST TERMINÉ")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
