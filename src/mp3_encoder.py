"""Module pour l'encodage audio en format MP3."""

import io
from pathlib import Path
from typing import Optional
from pydub import AudioSegment


class MP3Encoder:
    """Classe pour gérer l'encodage audio en temps réel vers le format MP3."""

    def __init__(
        self,
        output_file: Path,
        sample_rate: int = 44100,
        channels: int = 2,
        sample_width: int = 2,
        bitrate: str = "128k"
    ):
        """
        Initialise l'encodeur MP3.

        Args:
            output_file: Chemin du fichier MP3 de sortie
            sample_rate: Taux d'échantillonnage en Hz (par défaut 44100)
            channels: Nombre de canaux audio (1=mono, 2=stéréo)
            sample_width: Largeur d'échantillon en octets (2 pour 16-bit)
            bitrate: Bitrate MP3 (par défaut "128k")
        """
        self.output_file = output_file
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.bitrate = bitrate

        # Buffer pour accumuler les frames audio
        self.audio_buffer = io.BytesIO()
        self._is_closed = False

    def write_frames(self, frames: bytes):
        """
        Écrit des frames audio dans le buffer.

        Args:
            frames: Données audio brutes à encoder

        Raises:
            RuntimeError: Si l'encodeur a déjà été fermé
        """
        if self._is_closed:
            raise RuntimeError("L'encodeur MP3 a déjà été fermé")

        self.audio_buffer.write(frames)

    def close(self):
        """
        Finalise l'encodage et sauvegarde le fichier MP3.

        Raises:
            RuntimeError: Si l'encodage échoue (FFmpeg manquant, etc.)
        """
        if self._is_closed:
            return

        try:
            # Récupérer toutes les données audio du buffer
            audio_data = self.audio_buffer.getvalue()

            if len(audio_data) == 0:
                # Pas de données à encoder
                self._is_closed = True
                return

            # Créer un AudioSegment à partir des données brutes
            audio_segment = AudioSegment(
                data=audio_data,
                sample_width=self.sample_width,
                frame_rate=self.sample_rate,
                channels=self.channels
            )

            # Exporter en MP3
            audio_segment.export(
                str(self.output_file),
                format="mp3",
                bitrate=self.bitrate
            )

        except FileNotFoundError as e:
            raise RuntimeError(
                "FFmpeg n'est pas installé ou n'est pas dans le PATH. "
                "Installez FFmpeg pour encoder en MP3:\n"
                "  - Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                "  - macOS: brew install ffmpeg\n"
                "  - Fedora: sudo dnf install ffmpeg"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Erreur lors de l'encodage MP3: {e}") from e
        finally:
            self._is_closed = True
            self.audio_buffer.close()

    def __enter__(self):
        """Support du context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ferme automatiquement l'encodeur lors de la sortie du context."""
        self.close()
        return False
