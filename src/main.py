"""Point d'entrée principal pour l'enregistreur audio."""

import sys
import signal
import threading
import argparse
from pathlib import Path

from src.audio_recorder import AudioRecorder
from src.audio_devices import print_available_devices


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
    # Parser les arguments CLI
    parser = argparse.ArgumentParser(
        description="Enregistreur audio en continu avec encodage MP3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  %(prog)s                        # Enregistrer avec détection automatique
  %(prog)s --list-devices         # Lister les périphériques disponibles
  %(prog)s --device 5             # Enregistrer avec le périphérique #5
  %(prog)s --output ~/recordings  # Enregistrer dans ~/recordings
        """
    )
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help="Afficher la liste des périphériques audio disponibles et quitter"
    )
    parser.add_argument(
        '--device',
        type=int,
        metavar='INDEX',
        help="Spécifier l'index du périphérique audio à utiliser (voir --list-devices)"
    )
    parser.add_argument(
        '--output',
        type=str,
        metavar='DIR',
        default=str(Path.home() / "audio" / "enregistrements"),
        help="Répertoire de sortie pour les fichiers audio (défaut: ~/audio/enregistrements)"
    )
    parser.add_argument(
        '--bitrate',
        type=str,
        metavar='RATE',
        default='128k',
        help="Bitrate MP3 (défaut: 128k)"
    )

    args = parser.parse_args()

    # Si --list-devices, afficher les périphériques et quitter
    if args.list_devices:
        print("=" * 80)
        print("PÉRIPHÉRIQUES AUDIO DISPONIBLES")
        print("=" * 80)
        print()
        print_available_devices()
        return 0

    # Configurer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("ENREGISTREUR AUDIO EN CONTINU")
    print("=" * 60)
    print()

    # Créer l'enregistreur audio
    output_dir = Path(args.output).expanduser()
    recorder = AudioRecorder(
        output_dir=str(output_dir),
        bitrate=args.bitrate,
        device_index=args.device
    )

    print(f"Répertoire de sortie: {output_dir}")
    print(f"Format d'encodage: MP3 ({args.bitrate})")
    if args.device is not None:
        print(f"Source audio: Périphérique spécifié (index {args.device})")
    else:
        print(f"Source audio: Détection automatique (loopback)")
    print()

    try:
        # Démarrer l'enregistrement
        output_file = recorder.start_recording()
        print(f"✓ Enregistrement démarré")
        print(f"✓ Fichier: {output_file.name}")
        if recorder.device_name:
            print(f"✓ Périphérique: {recorder.device_name}")
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
        print("Arrêt de l'enregistrement et encodage MP3 en cours...")
        recorder.stop_recording()
        print("✓ Enregistrement terminé et encodé en MP3")
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
