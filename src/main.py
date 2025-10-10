"""Point d'entrée principal pour l'enregistreur audio."""

import sys
import signal
import threading
from pathlib import Path

from src.audio_recorder import AudioRecorder


def signal_handler(signum, frame):
    """Gestionnaire de signaux pour un arrêt propre."""
    print("\n\nInterruption détectée. Arrêt de l'enregistrement...")
    sys.exit(0)


def wait_for_exit_command(stop_event: threading.Event):
    """
    Attend que l'utilisateur tape 'exit' pour arrêter l'enregistrement.

    Args:
        stop_event: Event utilisé pour signaler l'arrêt
    """
    while not stop_event.is_set():
        try:
            user_input = input().strip().lower()
            if user_input == "exit":
                stop_event.set()
                break
        except EOFError:
            # Fin du flux d'entrée (peut arriver dans certains environnements)
            break
        except KeyboardInterrupt:
            # Ctrl+C détecté
            stop_event.set()
            break


def main():
    """Fonction principale pour démarrer l'enregistreur audio."""
    # Configurer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("ENREGISTREUR AUDIO EN CONTINU")
    print("=" * 60)
    print()

    # Créer l'enregistreur audio
    output_dir = Path.home() / "audio"
    recorder = AudioRecorder(output_dir=str(output_dir))

    print(f"Répertoire de sortie: {output_dir}")
    print()

    try:
        # Démarrer l'enregistrement
        output_file = recorder.start_recording()
        print(f"✓ Enregistrement démarré")
        print(f"✓ Fichier: {output_file.name}")
        print()
        print("Tapez 'exit' pour arrêter l'enregistrement, ou appuyez sur Ctrl+C")
        print("-" * 60)
        print()

        # Créer un Event pour signaler l'arrêt
        stop_event = threading.Event()

        # Démarrer le thread d'écoute de la commande exit
        exit_thread = threading.Thread(
            target=wait_for_exit_command,
            args=(stop_event,),
            daemon=True
        )
        exit_thread.start()

        # Attendre que l'utilisateur demande l'arrêt
        stop_event.wait()

        # Arrêter l'enregistrement
        print()
        print("Arrêt de l'enregistrement en cours...")
        recorder.stop_recording()
        print("✓ Enregistrement terminé et sauvegardé")
        print(f"✓ Fichier disponible: {output_file}")

    except PermissionError as e:
        print(f"✗ Erreur de permissions: {e}", file=sys.stderr)
        print(f"Vérifiez que vous avez les droits d'écriture sur {output_dir}", file=sys.stderr)
        sys.exit(1)

    except OSError as e:
        print(f"✗ Erreur d'accès au périphérique audio: {e}", file=sys.stderr)
        print("Vérifiez qu'un périphérique audio est disponible et que PortAudio est installé", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"✗ Erreur inattendue: {e}", file=sys.stderr)
        recorder.stop_recording()
        sys.exit(1)

    finally:
        print()
        print("=" * 60)
        print("Programme terminé")
        print("=" * 60)


if __name__ == "__main__":
    main()
