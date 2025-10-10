"""Module pour l'enregistrement audio en continu."""

import os
import wave
import pyaudio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional


class AudioRecorder:
    """Classe pour gérer l'enregistrement audio en continu."""

    def __init__(
        self,
        output_dir: str = "~/audio",
        sample_rate: int = 44100,
        channels: int = 2,
        chunk_size: int = 1024,
        audio_format: int = pyaudio.paInt16
    ):
        """
        Initialise l'enregistreur audio.

        Args:
            output_dir: Répertoire de sortie pour les fichiers audio
            sample_rate: Taux d'échantillonnage en Hz (par défaut 44100)
            channels: Nombre de canaux audio (1=mono, 2=stéréo)
            chunk_size: Taille des chunks de lecture audio
            audio_format: Format audio PyAudio (par défaut paInt16)
        """
        self.output_dir = Path(output_dir).expanduser()
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format

        # État interne
        self.is_recording = False
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.wave_file: Optional[wave.Wave_write] = None
        self.recording_thread: Optional[threading.Thread] = None

    def _generate_filename(self) -> Path:
        """
        Génère un nom de fichier horodaté.

        Returns:
            Chemin complet du fichier audio à créer
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.wav"
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
            RuntimeError: Si l'enregistrement est déjà en cours
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

            # Ouvrir le flux audio
            self.stream = self.pyaudio_instance.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            # Ouvrir le fichier WAV
            self.wave_file = wave.open(str(output_file), 'wb')
            self.wave_file.setnchannels(self.channels)
            self.wave_file.setsampwidth(
                self.pyaudio_instance.get_sample_size(self.audio_format)
            )
            self.wave_file.setframerate(self.sample_rate)

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
            raise RuntimeError(f"Erreur lors du démarrage de l'enregistrement: {e}")

    def _record_audio(self):
        """Boucle d'enregistrement audio (exécutée dans un thread séparé)."""
        try:
            while self.is_recording and self.stream and self.wave_file:
                # Lire les données audio
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                # Écrire dans le fichier WAV
                self.wave_file.writeframes(data)
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

        # Fermer le fichier WAV
        if self.wave_file:
            try:
                self.wave_file.close()
            except Exception:
                pass
            finally:
                self.wave_file = None

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
