"""Module pour l'enregistrement audio en continu."""

import os
import pyaudio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.audio_devices import find_loopback_device, get_device_info
from src.mp3_encoder import MP3Encoder


class AudioRecorder:
    """Classe pour gérer l'enregistrement audio en continu."""

    def __init__(
        self,
        output_dir: str = "~/audio/enregistrements",
        sample_rate: int = 44100,
        channels: int = 2,
        chunk_size: int = 1024,
        audio_format: int = pyaudio.paInt16,
        use_system_audio: bool = True,
        bitrate: str = "128k",
        device_index: Optional[int] = None
    ):
        """
        Initialise l'enregistreur audio.

        Args:
            output_dir: Répertoire de sortie pour les fichiers audio
            sample_rate: Taux d'échantillonnage en Hz (par défaut 44100)
            channels: Nombre de canaux audio (1=mono, 2=stéréo)
            chunk_size: Taille des chunks de lecture audio
            audio_format: Format audio PyAudio (par défaut paInt16)
            use_system_audio: Utiliser la capture système (loopback) au lieu du microphone
            bitrate: Bitrate pour l'encodage MP3 (par défaut "128k")
            device_index: Index du périphérique audio à utiliser (optionnel).
                         Si spécifié, remplace la détection automatique.
                         Utilisez --list-devices pour voir les périphériques disponibles.
        """
        self.output_dir = Path(output_dir).expanduser()
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format
        self.use_system_audio = use_system_audio
        self.bitrate = bitrate
        self.manual_device_index = device_index

        # État interne
        self.is_recording = False
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.mp3_encoder: Optional[MP3Encoder] = None
        self.recording_thread: Optional[threading.Thread] = None
        self.device_index: Optional[int] = None
        self.device_name: Optional[str] = None

    def _generate_filename(self) -> Path:
        """
        Génère un nom de fichier horodaté.

        Returns:
            Chemin complet du fichier audio à créer
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.mp3"
        return self.output_dir / filename

    def _ensure_output_dir(self):
        """Crée le répertoire de sortie s'il n'existe pas."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(
                f"Impossible de créer le répertoire {self.output_dir}: {e}"
            )

    def start_recording(self) -> Path:
        """
        Démarre l'enregistrement audio.

        Returns:
            Chemin du fichier en cours d'enregistrement

        Raises:
            RuntimeError: Si l'enregistrement est déjà en cours ou si aucun périphérique loopback n'est trouvé
            OSError: Si le périphérique audio n'est pas accessible
        """
        if self.is_recording:
            raise RuntimeError("L'enregistrement est déjà en cours")

        # Créer le répertoire de sortie
        self._ensure_output_dir()

        # Générer le nom de fichier
        output_file = self._generate_filename()

        try:
            # Initialiser PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()

            # Détecter le périphérique à utiliser
            if self.manual_device_index is not None:
                # Utiliser le périphérique spécifié manuellement
                self.device_index = self.manual_device_index
                device_info = get_device_info(self.device_index)
                if device_info is None:
                    raise ValueError(
                        f"Le périphérique avec l'index {self.device_index} n'existe pas.\n"
                        f"Utilisez --list-devices pour voir les périphériques disponibles."
                    )
                if device_info['maxInputChannels'] == 0:
                    raise ValueError(
                        f"Le périphérique '{device_info['name']}' (index {self.device_index}) "
                        f"ne peut pas capturer d'audio (maxInputChannels = 0).\n"
                        f"Utilisez --list-devices pour voir les périphériques disponibles."
                    )
                self.device_name = device_info['name']
            elif self.use_system_audio:
                # Détection automatique du périphérique loopback
                self.device_index = find_loopback_device()
                if self.device_index is None:
                    raise RuntimeError(
                        "Aucun périphérique de capture système (loopback) trouvé.\n"
                        "Solutions:\n"
                        "  1. Utilisez --list-devices pour voir les périphériques disponibles\n"
                        "  2. Spécifiez manuellement un périphérique avec --device INDEX\n"
                        "  3. Configurez un périphérique loopback:\n"
                        "     - Linux: Vérifiez que PulseAudio Monitor est activé (pactl list sources | grep -i monitor)\n"
                        "     - Windows: Activez 'Stereo Mix' dans les paramètres audio\n"
                        "     - macOS: Installez Soundflower ou BlackHole"
                    )
                device_info = get_device_info(self.device_index)
                if device_info:
                    self.device_name = device_info['name']
            else:
                # Utiliser le périphérique d'entrée par défaut (microphone)
                self.device_index = None
                self.device_name = "Microphone par défaut"

            # Ouvrir le flux audio
            self.stream = self.pyaudio_instance.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size
            )

            # Créer l'encodeur MP3
            sample_width = self.pyaudio_instance.get_sample_size(self.audio_format)
            self.mp3_encoder = MP3Encoder(
                output_file=output_file,
                sample_rate=self.sample_rate,
                channels=self.channels,
                sample_width=sample_width,
                bitrate=self.bitrate
            )

            # Démarrer l'enregistrement dans un thread séparé
            self.is_recording = True
            self.recording_thread = threading.Thread(
                target=self._record_audio,
                daemon=True
            )
            self.recording_thread.start()

            return output_file

        except OSError as e:
            self._cleanup()
            raise OSError(f"Erreur lors de l'accès au périphérique audio: {e}")
        except Exception as e:
            self._cleanup()
            raise

    def _record_audio(self):
        """Boucle d'enregistrement audio (exécutée dans un thread séparé)."""
        try:
            while self.is_recording and self.stream and self.mp3_encoder:
                # Lire les données audio
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                # Écrire dans l'encodeur MP3
                self.mp3_encoder.write_frames(data)
        except Exception as e:
            print(f"Erreur pendant l'enregistrement: {e}")
            self.is_recording = False

    def stop_recording(self):
        """Arrête l'enregistrement et nettoie les ressources."""
        if not self.is_recording:
            return

        # Arrêter l'enregistrement
        self.is_recording = False

        # Attendre que le thread d'enregistrement se termine
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)

        # Nettoyer les ressources
        self._cleanup()

    def _cleanup(self):
        """Nettoie les ressources PyAudio et ferme les fichiers."""
        # Fermer le flux audio
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            finally:
                self.stream = None

        # Fermer l'encodeur MP3
        if self.mp3_encoder:
            try:
                self.mp3_encoder.close()
            except Exception:
                pass
            finally:
                self.mp3_encoder = None

        # Terminer PyAudio
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception:
                pass
            finally:
                self.pyaudio_instance = None

    def __enter__(self):
        """Support du context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Nettoyage automatique lors de la sortie du context manager."""
        self.stop_recording()
        return False
