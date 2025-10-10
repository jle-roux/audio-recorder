"""Tests unitaires pour le module audio_recorder."""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.audio_recorder import AudioRecorder


class TestAudioRecorder:
    """Tests pour la classe AudioRecorder."""

    def test_init_default_values(self):
        """Teste l'initialisation avec les valeurs par défaut."""
        recorder = AudioRecorder()

        assert recorder.output_dir == Path.home() / "audio"
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2
        assert recorder.chunk_size == 1024
        assert recorder.is_recording is False
        assert recorder.pyaudio_instance is None
        assert recorder.stream is None
        assert recorder.wave_file is None

    def test_init_custom_values(self):
        """Teste l'initialisation avec des valeurs personnalisées."""
        custom_dir = "/tmp/test_audio"
        recorder = AudioRecorder(
            output_dir=custom_dir,
            sample_rate=48000,
            channels=1,
            chunk_size=2048
        )

        assert recorder.output_dir == Path(custom_dir)
        assert recorder.sample_rate == 48000
        assert recorder.channels == 1
        assert recorder.chunk_size == 2048

    def test_generate_filename(self):
        """Teste la génération de noms de fichiers horodatés."""
        recorder = AudioRecorder(output_dir="/tmp/test")

        # Mock datetime pour un résultat prévisible
        with patch('src.audio_recorder.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 10, 14, 30, 45)
            filename = recorder._generate_filename()

        expected_path = Path("/tmp/test/2025-10-10_14-30-45.wav")
        assert filename == expected_path

    def test_ensure_output_dir_creates_directory(self, tmp_path):
        """Teste que le répertoire de sortie est créé s'il n'existe pas."""
        output_dir = tmp_path / "new_audio_dir"
        recorder = AudioRecorder(output_dir=str(output_dir))

        assert not output_dir.exists()
        recorder._ensure_output_dir()
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_ensure_output_dir_permission_error(self):
        """Teste la gestion des erreurs de permissions."""
        # Utiliser un chemin qui nécessite des permissions root
        recorder = AudioRecorder(output_dir="/root/audio_test_forbidden")

        with pytest.raises(PermissionError) as exc_info:
            recorder._ensure_output_dir()

        assert "Impossible de créer le répertoire" in str(exc_info.value)

    @patch('src.audio_recorder.pyaudio.PyAudio')
    @patch('src.audio_recorder.wave.open')
    def test_start_recording_success(self, mock_wave_open, mock_pyaudio_class, tmp_path):
        """Teste le démarrage réussi de l'enregistrement."""
        output_dir = tmp_path / "audio"
        recorder = AudioRecorder(output_dir=str(output_dir))

        # Configuration des mocks
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_stream = Mock()
        mock_pyaudio_instance.open.return_value = mock_stream
        mock_pyaudio_instance.get_sample_size.return_value = 2
        mock_wave_file = Mock()
        mock_wave_open.return_value = mock_wave_file

        # Démarrer l'enregistrement
        output_file = recorder.start_recording()

        # Vérifications
        assert recorder.is_recording is True
        assert output_dir.exists()
        assert output_file.parent == output_dir
        assert output_file.name.endswith('.wav')
        mock_pyaudio_instance.open.assert_called_once()
        mock_wave_file.setnchannels.assert_called_once_with(2)
        mock_wave_file.setframerate.assert_called_once_with(44100)

        # Nettoyer
        recorder.stop_recording()

    @patch('src.audio_recorder.pyaudio.PyAudio')
    def test_start_recording_already_recording(self, mock_pyaudio_class, tmp_path):
        """Teste qu'on ne peut pas démarrer un enregistrement déjà en cours."""
        recorder = AudioRecorder(output_dir=str(tmp_path))
        recorder.is_recording = True

        with pytest.raises(RuntimeError) as exc_info:
            recorder.start_recording()

        assert "déjà en cours" in str(exc_info.value)

    @patch('src.audio_recorder.pyaudio.PyAudio')
    def test_start_recording_audio_device_error(self, mock_pyaudio_class, tmp_path):
        """Teste la gestion des erreurs de périphérique audio."""
        recorder = AudioRecorder(output_dir=str(tmp_path))

        # Simuler une erreur lors de l'ouverture du stream
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.open.side_effect = OSError("Périphérique non trouvé")

        with pytest.raises(OSError) as exc_info:
            recorder.start_recording()

        assert "périphérique audio" in str(exc_info.value).lower()

    @patch('src.audio_recorder.pyaudio.PyAudio')
    @patch('src.audio_recorder.wave.open')
    def test_stop_recording(self, mock_wave_open, mock_pyaudio_class, tmp_path):
        """Teste l'arrêt de l'enregistrement."""
        recorder = AudioRecorder(output_dir=str(tmp_path))

        # Configuration des mocks
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_stream = Mock()
        mock_pyaudio_instance.open.return_value = mock_stream
        mock_pyaudio_instance.get_sample_size.return_value = 2
        mock_wave_file = Mock()
        mock_wave_open.return_value = mock_wave_file

        # Démarrer puis arrêter
        recorder.start_recording()
        recorder.stop_recording()

        # Vérifications
        assert recorder.is_recording is False
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_wave_file.close.assert_called_once()
        mock_pyaudio_instance.terminate.assert_called_once()

    def test_stop_recording_when_not_recording(self):
        """Teste que stop_recording ne fait rien si pas d'enregistrement en cours."""
        recorder = AudioRecorder()
        # Ne devrait pas lever d'exception
        recorder.stop_recording()

    @patch('src.audio_recorder.pyaudio.PyAudio')
    @patch('src.audio_recorder.wave.open')
    def test_context_manager(self, mock_wave_open, mock_pyaudio_class, tmp_path):
        """Teste l'utilisation en tant que context manager."""
        # Configuration des mocks
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_stream = Mock()
        mock_pyaudio_instance.open.return_value = mock_stream
        mock_pyaudio_instance.get_sample_size.return_value = 2
        mock_wave_file = Mock()
        mock_wave_open.return_value = mock_wave_file

        with AudioRecorder(output_dir=str(tmp_path)) as recorder:
            recorder.start_recording()
            assert recorder.is_recording is True

        # Après la sortie du context, l'enregistrement devrait être arrêté
        assert recorder.is_recording is False
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()

    @patch('src.audio_recorder.pyaudio.PyAudio')
    @patch('src.audio_recorder.wave.open')
    def test_cleanup_handles_exceptions(self, mock_wave_open, mock_pyaudio_class, tmp_path):
        """Teste que _cleanup gère les exceptions lors du nettoyage."""
        recorder = AudioRecorder(output_dir=str(tmp_path))

        # Configuration des mocks avec exceptions
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_stream = Mock()
        mock_stream.stop_stream.side_effect = Exception("Erreur de fermeture")
        mock_pyaudio_instance.open.return_value = mock_stream
        mock_pyaudio_instance.get_sample_size.return_value = 2
        mock_wave_file = Mock()
        mock_wave_file.close.side_effect = Exception("Erreur de fermeture fichier")
        mock_wave_open.return_value = mock_wave_file

        # Démarrer et arrêter - ne devrait pas lever d'exception
        recorder.start_recording()
        recorder.stop_recording()

        # Vérifier que les ressources sont à None malgré les exceptions
        assert recorder.stream is None
        assert recorder.wave_file is None
        assert recorder.pyaudio_instance is None
