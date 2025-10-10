"""Tests pour le module de détection de périphériques audio."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.audio_devices import (
    list_audio_devices,
    find_loopback_device,
    get_device_info,
    print_available_devices
)


class TestListAudioDevices:
    """Tests pour la fonction list_audio_devices."""

    @patch('src.audio_devices.pyaudio.PyAudio')
    def test_list_audio_devices_success(self, mock_pyaudio_class):
        """Test que list_audio_devices retourne la liste des périphériques."""
        # Configurer le mock
        mock_pa = Mock()
        mock_pyaudio_class.return_value = mock_pa
        mock_pa.get_device_count.return_value = 2

        mock_pa.get_device_info_by_index.side_effect = [
            {
                'name': 'Microphone',
                'maxInputChannels': 2,
                'defaultSampleRate': 44100.0
            },
            {
                'name': 'Monitor of Built-in Audio',
                'maxInputChannels': 2,
                'defaultSampleRate': 44100.0
            }
        ]

        # Exécuter
        devices = list_audio_devices()

        # Vérifier
        assert len(devices) == 2
        assert devices[0]['index'] == 0
        assert devices[0]['name'] == 'Microphone'
        assert devices[0]['maxInputChannels'] == 2
        assert devices[1]['index'] == 1
        assert devices[1]['name'] == 'Monitor of Built-in Audio'
        mock_pa.terminate.assert_called_once()

    @patch('src.audio_devices.pyaudio.PyAudio')
    def test_list_audio_devices_empty(self, mock_pyaudio_class):
        """Test que list_audio_devices retourne une liste vide si aucun périphérique."""
        # Configurer le mock
        mock_pa = Mock()
        mock_pyaudio_class.return_value = mock_pa
        mock_pa.get_device_count.return_value = 0

        # Exécuter
        devices = list_audio_devices()

        # Vérifier
        assert devices == []
        mock_pa.terminate.assert_called_once()

    @patch('src.audio_devices.pyaudio.PyAudio')
    def test_list_audio_devices_with_errors(self, mock_pyaudio_class):
        """Test que list_audio_devices ignore les périphériques inaccessibles."""
        # Configurer le mock
        mock_pa = Mock()
        mock_pyaudio_class.return_value = mock_pa
        mock_pa.get_device_count.return_value = 3

        mock_pa.get_device_info_by_index.side_effect = [
            {'name': 'Device 1', 'maxInputChannels': 2, 'defaultSampleRate': 44100.0},
            Exception("Device not accessible"),
            {'name': 'Device 3', 'maxInputChannels': 1, 'defaultSampleRate': 48000.0}
        ]

        # Exécuter
        devices = list_audio_devices()

        # Vérifier - le périphérique 2 doit être ignoré
        assert len(devices) == 2
        assert devices[0]['name'] == 'Device 1'
        assert devices[1]['name'] == 'Device 3'


class TestFindLoopbackDevice:
    """Tests pour la fonction find_loopback_device."""

    @patch('src.audio_devices.list_audio_devices')
    def test_find_loopback_device_monitor(self, mock_list_devices):
        """Test que find_loopback_device trouve un périphérique Monitor."""
        # Configurer le mock
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Microphone', 'maxInputChannels': 2, 'defaultSampleRate': 44100},
            {'index': 1, 'name': 'Monitor of Built-in Audio', 'maxInputChannels': 2, 'defaultSampleRate': 44100},
            {'index': 2, 'name': 'Speakers', 'maxInputChannels': 0, 'defaultSampleRate': 44100}
        ]

        # Exécuter
        index = find_loopback_device()

        # Vérifier
        assert index == 1

    @patch('src.audio_devices.list_audio_devices')
    def test_find_loopback_device_stereo_mix(self, mock_list_devices):
        """Test que find_loopback_device trouve Stereo Mix (Windows)."""
        # Configurer le mock
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Microphone Array', 'maxInputChannels': 2, 'defaultSampleRate': 44100},
            {'index': 1, 'name': 'Stereo Mix', 'maxInputChannels': 2, 'defaultSampleRate': 44100}
        ]

        # Exécuter
        index = find_loopback_device()

        # Vérifier
        assert index == 1

    @patch('src.audio_devices.list_audio_devices')
    def test_find_loopback_device_blackhole(self, mock_list_devices):
        """Test que find_loopback_device trouve BlackHole (macOS)."""
        # Configurer le mock
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Built-in Microphone', 'maxInputChannels': 2, 'defaultSampleRate': 44100},
            {'index': 1, 'name': 'BlackHole 2ch', 'maxInputChannels': 2, 'defaultSampleRate': 48000}
        ]

        # Exécuter
        index = find_loopback_device()

        # Vérifier
        assert index == 1

    @patch('src.audio_devices.list_audio_devices')
    def test_find_loopback_device_not_found(self, mock_list_devices):
        """Test que find_loopback_device retourne None si aucun loopback."""
        # Configurer le mock
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Microphone', 'maxInputChannels': 2, 'defaultSampleRate': 44100},
            {'index': 1, 'name': 'Line In', 'maxInputChannels': 2, 'defaultSampleRate': 44100}
        ]

        # Exécuter
        index = find_loopback_device()

        # Vérifier
        assert index is None

    @patch('src.audio_devices.list_audio_devices')
    def test_find_loopback_device_ignores_output_only(self, mock_list_devices):
        """Test que find_loopback_device ignore les périphériques sans entrée."""
        # Configurer le mock
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Microphone', 'maxInputChannels': 2, 'defaultSampleRate': 44100},
            {'index': 1, 'name': 'Monitor of Speakers', 'maxInputChannels': 0, 'defaultSampleRate': 44100}
        ]

        # Exécuter
        index = find_loopback_device()

        # Vérifier - doit ignorer le Monitor car maxInputChannels == 0
        assert index is None


class TestGetDeviceInfo:
    """Tests pour la fonction get_device_info."""

    @patch('src.audio_devices.pyaudio.PyAudio')
    def test_get_device_info_success(self, mock_pyaudio_class):
        """Test que get_device_info retourne les informations du périphérique."""
        # Configurer le mock
        mock_pa = Mock()
        mock_pyaudio_class.return_value = mock_pa
        mock_pa.get_device_info_by_index.return_value = {
            'name': 'Test Device',
            'maxInputChannels': 2,
            'maxOutputChannels': 2,
            'defaultSampleRate': 44100.0,
            'defaultLowInputLatency': 0.01,
            'defaultHighInputLatency': 0.1
        }

        # Exécuter
        info = get_device_info(1)

        # Vérifier
        assert info is not None
        assert info['index'] == 1
        assert info['name'] == 'Test Device'
        assert info['maxInputChannels'] == 2
        assert info['maxOutputChannels'] == 2
        mock_pa.terminate.assert_called_once()

    @patch('src.audio_devices.pyaudio.PyAudio')
    def test_get_device_info_not_found(self, mock_pyaudio_class):
        """Test que get_device_info retourne None si le périphérique n'existe pas."""
        # Configurer le mock
        mock_pa = Mock()
        mock_pyaudio_class.return_value = mock_pa
        mock_pa.get_device_info_by_index.side_effect = Exception("Device not found")

        # Exécuter
        info = get_device_info(999)

        # Vérifier
        assert info is None
        mock_pa.terminate.assert_called_once()


class TestPrintAvailableDevices:
    """Tests pour la fonction print_available_devices."""

    @patch('src.audio_devices.find_loopback_device')
    @patch('src.audio_devices.list_audio_devices')
    @patch('builtins.print')
    def test_print_available_devices_with_loopback(
        self, mock_print, mock_list_devices, mock_find_loopback
    ):
        """Test que print_available_devices affiche correctement les périphériques."""
        # Configurer les mocks
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Microphone', 'maxInputChannels': 2, 'defaultSampleRate': 44100},
            {'index': 1, 'name': 'Monitor', 'maxInputChannels': 2, 'defaultSampleRate': 44100}
        ]
        mock_find_loopback.return_value = 1

        # Exécuter
        print_available_devices()

        # Vérifier que print a été appelé
        assert mock_print.call_count > 0
        # Vérifier qu'on mentionne le périphérique loopback détecté
        calls = [str(call) for call in mock_print.call_args_list]
        assert any('loopback' in str(call).lower() for call in calls)

    @patch('src.audio_devices.find_loopback_device')
    @patch('src.audio_devices.list_audio_devices')
    @patch('builtins.print')
    def test_print_available_devices_without_loopback(
        self, mock_print, mock_list_devices, mock_find_loopback
    ):
        """Test l'affichage quand aucun loopback n'est trouvé."""
        # Configurer les mocks
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Microphone', 'maxInputChannels': 2, 'defaultSampleRate': 44100}
        ]
        mock_find_loopback.return_value = None

        # Exécuter
        print_available_devices()

        # Vérifier que print a été appelé
        assert mock_print.call_count > 0
        # Vérifier qu'on mentionne l'absence de loopback
        calls = [str(call) for call in mock_print.call_args_list]
        assert any('aucun' in str(call).lower() for call in calls)
