"""Tests pour le module d'encodage MP3."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.mp3_encoder import MP3Encoder


class TestMP3Encoder:
    """Tests pour la classe MP3Encoder."""

    def test_init(self):
        """Test que MP3Encoder s'initialise correctement."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(
            output_file=output_file,
            sample_rate=44100,
            channels=2,
            sample_width=2,
            bitrate="128k"
        )

        assert encoder.output_file == output_file
        assert encoder.sample_rate == 44100
        assert encoder.channels == 2
        assert encoder.sample_width == 2
        assert encoder.bitrate == "128k"
        assert encoder._is_closed is False

    def test_write_frames(self):
        """Test que write_frames écrit dans le buffer."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(output_file=output_file)

        # Écrire des données
        test_data = b'\x00\x01\x02\x03'
        encoder.write_frames(test_data)

        # Vérifier que les données sont dans le buffer
        assert encoder.audio_buffer.getvalue() == test_data

    def test_write_frames_multiple(self):
        """Test que plusieurs write_frames accumulent les données."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(output_file=output_file)

        # Écrire plusieurs fois
        encoder.write_frames(b'\x00\x01')
        encoder.write_frames(b'\x02\x03')
        encoder.write_frames(b'\x04\x05')

        # Vérifier que toutes les données sont dans le buffer
        assert encoder.audio_buffer.getvalue() == b'\x00\x01\x02\x03\x04\x05'

    def test_write_frames_after_close_raises_error(self):
        """Test que write_frames lève une erreur si l'encodeur est fermé."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(output_file=output_file)
        encoder._is_closed = True

        with pytest.raises(RuntimeError, match="L'encodeur MP3 a déjà été fermé"):
            encoder.write_frames(b'\x00\x01')

    @patch('src.mp3_encoder.AudioSegment')
    def test_close_success(self, mock_audio_segment_class):
        """Test que close encode et sauvegarde le fichier MP3."""
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            output_file = Path(tmp.name)

        try:
            # Configurer le mock
            mock_segment = Mock()
            mock_audio_segment_class.return_value = mock_segment

            # Créer l'encodeur et écrire des données
            encoder = MP3Encoder(output_file=output_file)
            encoder.write_frames(b'\x00\x01\x02\x03' * 1000)

            # Fermer
            encoder.close()

            # Vérifier que AudioSegment a été créé avec les bons paramètres
            mock_audio_segment_class.assert_called_once()
            call_kwargs = mock_audio_segment_class.call_args[1]
            assert call_kwargs['sample_width'] == 2
            assert call_kwargs['frame_rate'] == 44100
            assert call_kwargs['channels'] == 2

            # Vérifier que export a été appelé
            mock_segment.export.assert_called_once()
            export_args = mock_segment.export.call_args
            assert str(output_file) in str(export_args[0])
            assert export_args[1]['format'] == 'mp3'
            assert export_args[1]['bitrate'] == '128k'

            # Vérifier que l'encodeur est marqué comme fermé
            assert encoder._is_closed is True

        finally:
            # Nettoyer le fichier temporaire
            if output_file.exists():
                output_file.unlink()

    @patch('src.mp3_encoder.AudioSegment')
    def test_close_empty_data(self, mock_audio_segment_class):
        """Test que close ne fait rien si aucune donnée n'a été écrite."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(output_file=output_file)

        # Fermer sans écrire de données
        encoder.close()

        # Vérifier que AudioSegment n'a pas été appelé
        mock_audio_segment_class.assert_not_called()

        # Vérifier que l'encodeur est marqué comme fermé
        assert encoder._is_closed is True

    def test_close_idempotent(self):
        """Test que close peut être appelé plusieurs fois sans erreur."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(output_file=output_file)

        # Fermer plusieurs fois
        encoder.close()
        encoder.close()
        encoder.close()

        # Pas d'exception levée
        assert encoder._is_closed is True

    @patch('src.mp3_encoder.AudioSegment')
    def test_close_ffmpeg_not_found(self, mock_audio_segment_class):
        """Test que close lève une erreur si FFmpeg n'est pas installé."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(output_file=output_file)
        encoder.write_frames(b'\x00\x01\x02\x03')

        # Simuler que FFmpeg n'est pas trouvé
        mock_segment = Mock()
        mock_audio_segment_class.return_value = mock_segment
        mock_segment.export.side_effect = FileNotFoundError("ffmpeg not found")

        # Vérifier que l'erreur est levée avec un message utile
        with pytest.raises(RuntimeError, match="FFmpeg n'est pas installé"):
            encoder.close()

    @patch('src.mp3_encoder.AudioSegment')
    def test_close_encoding_error(self, mock_audio_segment_class):
        """Test que close lève une erreur si l'encodage échoue."""
        output_file = Path("/tmp/test.mp3")
        encoder = MP3Encoder(output_file=output_file)
        encoder.write_frames(b'\x00\x01\x02\x03')

        # Simuler une erreur d'encodage
        mock_segment = Mock()
        mock_audio_segment_class.return_value = mock_segment
        mock_segment.export.side_effect = Exception("Encoding failed")

        # Vérifier que l'erreur est levée
        with pytest.raises(RuntimeError, match="Erreur lors de l'encodage MP3"):
            encoder.close()

    @patch('src.mp3_encoder.AudioSegment')
    def test_context_manager(self, mock_audio_segment_class):
        """Test que MP3Encoder fonctionne comme context manager."""
        output_file = Path("/tmp/test.mp3")

        # Configurer le mock
        mock_segment = Mock()
        mock_audio_segment_class.return_value = mock_segment

        # Utiliser comme context manager
        with MP3Encoder(output_file=output_file) as encoder:
            encoder.write_frames(b'\x00\x01\x02\x03')
            assert encoder._is_closed is False

        # Vérifier que close a été appelé automatiquement
        assert encoder._is_closed is True
        mock_segment.export.assert_called_once()

    @patch('src.mp3_encoder.AudioSegment')
    def test_custom_bitrate(self, mock_audio_segment_class):
        """Test que le bitrate personnalisé est utilisé."""
        output_file = Path("/tmp/test.mp3")

        # Configurer le mock
        mock_segment = Mock()
        mock_audio_segment_class.return_value = mock_segment

        # Créer avec un bitrate personnalisé
        encoder = MP3Encoder(output_file=output_file, bitrate="256k")
        encoder.write_frames(b'\x00\x01\x02\x03')
        encoder.close()

        # Vérifier que le bon bitrate a été utilisé
        export_args = mock_segment.export.call_args
        assert export_args[1]['bitrate'] == '256k'
