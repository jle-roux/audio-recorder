"""Module pour la détection et gestion des périphériques audio."""

import pyaudio
import platform
from typing import Optional, List, Dict

# Import conditionnel pour PulseAudio sur Linux
try:
    import pulsectl
    PULSECTL_AVAILABLE = True
except ImportError:
    PULSECTL_AVAILABLE = False


def list_audio_devices() -> List[Dict]:
    """
    Liste tous les périphériques audio disponibles.

    Returns:
        Liste de dictionnaires contenant les informations des périphériques
        Chaque dictionnaire contient: index, name, maxInputChannels, defaultSampleRate
    """
    devices = []
    p = pyaudio.PyAudio()

    try:
        device_count = p.get_device_count()
        for i in range(device_count):
            try:
                info = p.get_device_info_by_index(i)
                devices.append({
                    'index': i,
                    'name': info.get('name', ''),
                    'maxInputChannels': info.get('maxInputChannels', 0),
                    'defaultSampleRate': info.get('defaultSampleRate', 0)
                })
            except Exception:
                # Ignorer les périphériques inaccessibles
                continue
    finally:
        p.terminate()

    return devices


def find_default_sink_monitor() -> Optional[Dict]:
    """
    Trouve le périphérique Monitor associé au sink (sortie audio) par défaut.

    Cette fonction est la méthode recommandée pour capturer l'audio système,
    car elle utilise le sink actif par défaut.

    Returns:
        Dictionnaire avec les informations du Monitor par défaut, ou None si non trouvé
        Format: {'name': str, 'description': str, 'index': int, 'monitor_of_sink': int}
    """
    if not PULSECTL_AVAILABLE:
        return None

    if platform.system() != 'Linux':
        return None

    try:
        with pulsectl.Pulse('audio-recorder-detection') as pulse:
            # Obtenir le sink par défaut
            default_sink_name = pulse.server_info().default_sink_name
            if not default_sink_name:
                return None

            # Trouver le sink par défaut dans la liste
            sinks = pulse.sink_list()
            default_sink = None
            for sink in sinks:
                if sink.name == default_sink_name:
                    default_sink = sink
                    break

            if not default_sink:
                return None

            # Trouver le Monitor de ce sink
            sources = pulse.source_list()
            for source in sources:
                if hasattr(source, 'monitor_of_sink') and source.monitor_of_sink == default_sink.index:
                    return {
                        'name': source.name,
                        'description': source.description,
                        'index': source.index,
                        'monitor_of_sink': source.monitor_of_sink,
                        'is_default': True
                    }
    except Exception as e:
        # Si PulseAudio n'est pas disponible, retourner None
        import logging
        logging.debug(f"Erreur lors de la détection du Monitor par défaut: {e}")
        pass

    return None


def get_pulseaudio_monitor_devices() -> List[Dict]:
    """
    Récupère la liste de TOUS les périphériques Monitor PulseAudio/PipeWire.

    Cette fonction liste maintenant TOUS les Monitors disponibles, pas seulement
    ceux avec monitor_of_sink défini, pour couvrir plus de cas d'usage.

    Returns:
        Liste de dictionnaires avec les informations des Monitor sources
        Format: [{'name': str, 'description': str, 'index': int, 'is_monitor': bool}, ...]
    """
    if not PULSECTL_AVAILABLE:
        return []

    if platform.system() != 'Linux':
        return []

    monitors = []
    try:
        with pulsectl.Pulse('audio-recorder-detection') as pulse:
            sources = pulse.source_list()
            for source in sources:
                # Détecter les Monitors de plusieurs façons
                is_monitor = False
                monitor_of_sink = None

                # Méthode 1 : Vérifier l'attribut monitor_of_sink
                if hasattr(source, 'monitor_of_sink') and source.monitor_of_sink is not None:
                    is_monitor = True
                    monitor_of_sink = source.monitor_of_sink

                # Méthode 2 : Vérifier si "monitor" est dans le nom
                if 'monitor' in source.name.lower():
                    is_monitor = True

                # Méthode 3 : Vérifier les propriétés du périphérique
                if hasattr(source, 'proplist'):
                    device_class = source.proplist.get('device.class', '')
                    if device_class == 'monitor':
                        is_monitor = True

                if is_monitor:
                    monitors.append({
                        'name': source.name,
                        'description': source.description,
                        'index': source.index,
                        'monitor_of_sink': monitor_of_sink,
                        'is_hdmi': 'hdmi' in source.description.lower() or 'displayport' in source.description.lower()
                    })
    except Exception as e:
        # Si PulseAudio n'est pas disponible, retourner une liste vide
        import logging
        logging.debug(f"Erreur lors de la détection des Monitors PulseAudio: {e}")
        pass

    return monitors


def map_pulseaudio_to_pyaudio(pulse_source_name: str, pulse_description: str = "") -> Optional[int]:
    """
    Trouve l'index PyAudio correspondant à un périphérique PulseAudio.

    Cette fonction utilise plusieurs stratégies de correspondance pour améliorer
    la fiabilité du mapping entre PulseAudio et PyAudio.

    Args:
        pulse_source_name: Nom du périphérique PulseAudio
        pulse_description: Description du périphérique PulseAudio (optionnel)

    Returns:
        Index PyAudio du périphérique, ou None si non trouvé
    """
    import logging
    devices = list_audio_devices()

    pulse_name_lower = pulse_source_name.lower()
    pulse_desc_lower = pulse_description.lower() if pulse_description else ""

    logging.debug(f"Tentative de mapping: PulseAudio '{pulse_source_name}' vers PyAudio")

    # Stratégie 1 : Correspondance exacte du nom
    for device in devices:
        device_name = device['name'].lower()
        if pulse_name_lower == device_name:
            logging.debug(f"  ✓ Correspondance exacte trouvée: index {device['index']}")
            return device['index']

    # Stratégie 2 : Le nom PulseAudio est contenu dans le nom PyAudio
    for device in devices:
        device_name = device['name'].lower()
        if pulse_name_lower in device_name:
            logging.debug(f"  ✓ Nom PulseAudio trouvé dans PyAudio: index {device['index']}")
            return device['index']

    # Stratégie 3 : Le nom PyAudio est contenu dans le nom PulseAudio
    for device in devices:
        device_name = device['name'].lower()
        if device_name in pulse_name_lower:
            logging.debug(f"  ✓ Nom PyAudio trouvé dans PulseAudio: index {device['index']}")
            return device['index']

    # Stratégie 4 : Correspondance partielle par description
    if pulse_desc_lower:
        for device in devices:
            device_name = device['name'].lower()
            # Extraire des mots-clés de la description
            desc_keywords = pulse_desc_lower.split()
            matches = sum(1 for keyword in desc_keywords if len(keyword) > 3 and keyword in device_name)
            if matches >= 2:  # Au moins 2 mots-clés correspondent
                logging.debug(f"  ✓ Correspondance par description: index {device['index']}")
                return device['index']

    # Stratégie 5 : Fallback vers le premier périphérique avec "pulse" dans le nom
    # ET qui peut capturer de l'audio
    for device in devices:
        if device['maxInputChannels'] > 0 and 'pulse' in device['name'].lower():
            logging.debug(f"  ⚠ Fallback vers périphérique Pulse: index {device['index']}")
            return device['index']

    logging.debug(f"  ✗ Aucune correspondance trouvée")
    return None


def find_loopback_device() -> Optional[int]:
    """
    Trouve le périphérique de loopback/monitor système pour la capture audio.

    Cette fonction utilise une approche multi-niveau pour maximiser les chances
    de trouver un périphérique de capture système:
    1. Détecte le Monitor du sink par défaut (recommandé)
    2. Recherche parmi tous les Monitors PulseAudio/PipeWire
    3. Fallback vers recherche par mots-clés dans PyAudio

    Sur Linux avec PulseAudio/PipeWire, utilise l'API PulseAudio pour détecter les Monitor sources.
    Sur Windows, recherche les périphériques WASAPI Loopback.
    Sur macOS, recherche Soundflower ou BlackHole.

    Returns:
        Index du périphérique de loopback, ou None si aucun n'est trouvé
    """
    import logging

    # Sur Linux, essayer d'abord avec PulseAudio
    if platform.system() == 'Linux' and PULSECTL_AVAILABLE:
        logging.debug("Détection du périphérique loopback sur Linux avec PulseAudio/PipeWire")

        # Stratégie 1 : Utiliser le Monitor du sink par défaut (RECOMMANDÉ)
        logging.debug("  Stratégie 1: Détection du Monitor du sink par défaut")
        default_monitor = find_default_sink_monitor()
        if default_monitor:
            logging.debug(f"    ✓ Monitor par défaut trouvé: {default_monitor['description']}")
            pyaudio_index = map_pulseaudio_to_pyaudio(
                default_monitor['name'],
                default_monitor['description']
            )
            if pyaudio_index is not None:
                logging.debug(f"    ✓ Mappé vers PyAudio index: {pyaudio_index}")
                return pyaudio_index
            else:
                logging.debug(f"    ✗ Impossible de mapper vers PyAudio")

        # Stratégie 2 : Lister tous les Monitors et choisir le meilleur
        logging.debug("  Stratégie 2: Recherche parmi tous les Monitors disponibles")
        monitors = get_pulseaudio_monitor_devices()
        if monitors:
            logging.debug(f"    {len(monitors)} Monitor(s) détecté(s)")

            # Prioriser les Monitors non-HDMI
            non_hdmi_monitors = [m for m in monitors if not m.get('is_hdmi', False)]
            if non_hdmi_monitors:
                logging.debug(f"    {len(non_hdmi_monitors)} Monitor(s) non-HDMI")
                for monitor in non_hdmi_monitors:
                    logging.debug(f"      Tentative: {monitor['description']}")
                    pyaudio_index = map_pulseaudio_to_pyaudio(
                        monitor['name'],
                        monitor['description']
                    )
                    if pyaudio_index is not None:
                        logging.debug(f"      ✓ Mappé vers PyAudio index: {pyaudio_index}")
                        return pyaudio_index

            # Si aucun Monitor non-HDMI ne fonctionne, essayer tous les Monitors
            logging.debug("    Tentative avec tous les Monitors (y compris HDMI)")
            for monitor in monitors:
                logging.debug(f"      Tentative: {monitor['description']}")
                pyaudio_index = map_pulseaudio_to_pyaudio(
                    monitor['name'],
                    monitor['description']
                )
                if pyaudio_index is not None:
                    logging.debug(f"      ✓ Mappé vers PyAudio index: {pyaudio_index}")
                    return pyaudio_index

    # Stratégie 3 : Fallback via recherche par mots-clés dans PyAudio
    logging.debug("  Stratégie 3: Recherche par mots-clés dans PyAudio")
    devices = list_audio_devices()

    # Mots-clés pour identifier les périphériques de loopback selon la plateforme
    loopback_keywords = [
        'monitor',      # PulseAudio Monitor (Linux)
        'stereo mix',   # Windows Stereo Mix
        'wave out mix', # Windows Wave Out Mix
        'loopback',     # Loopback générique
        'soundflower',  # macOS Soundflower
        'blackhole',    # macOS BlackHole
        'what u hear',  # Autre nom pour Stereo Mix
    ]

    for device in devices:
        # Vérifier que le périphérique peut capturer de l'audio
        if device['maxInputChannels'] == 0:
            continue

        device_name = device['name'].lower()

        # Chercher les mots-clés de loopback dans le nom
        for keyword in loopback_keywords:
            if keyword in device_name:
                logging.debug(f"    ✓ Périphérique trouvé par mot-clé '{keyword}': index {device['index']}")
                return device['index']

    logging.debug("  ✗ Aucun périphérique loopback trouvé")
    return None


def get_device_info(device_index: int) -> Optional[Dict]:
    """
    Récupère les informations détaillées d'un périphérique audio.

    Args:
        device_index: Index du périphérique

    Returns:
        Dictionnaire avec les informations du périphérique, ou None si non trouvé
    """
    p = pyaudio.PyAudio()

    try:
        info = p.get_device_info_by_index(device_index)
        return {
            'index': device_index,
            'name': info.get('name', ''),
            'maxInputChannels': info.get('maxInputChannels', 0),
            'maxOutputChannels': info.get('maxOutputChannels', 0),
            'defaultSampleRate': info.get('defaultSampleRate', 0),
            'defaultLowInputLatency': info.get('defaultLowInputLatency', 0),
            'defaultHighInputLatency': info.get('defaultHighInputLatency', 0),
        }
    except Exception:
        return None
    finally:
        p.terminate()


def print_available_devices():
    """
    Affiche la liste de tous les périphériques audio disponibles.
    Utile pour le débogage et la configuration.
    """
    # Afficher les Monitors PulseAudio si disponible
    if platform.system() == 'Linux' and PULSECTL_AVAILABLE:
        print("🔍 Détection PulseAudio/PipeWire")
        print("-" * 80)

        # Afficher le Monitor par défaut
        default_monitor = find_default_sink_monitor()
        if default_monitor:
            print(f"✓ Monitor par défaut du système détecté:")
            print(f"  {default_monitor['description']}")
            pyaudio_index = map_pulseaudio_to_pyaudio(
                default_monitor['name'],
                default_monitor['description']
            )
            if pyaudio_index is not None:
                print(f"  → Mappé vers PyAudio index: {pyaudio_index} ⭐ RECOMMANDÉ")
            else:
                print(f"  → Non accessible via PyAudio")
            print()

        # Afficher tous les Monitors
        monitors = get_pulseaudio_monitor_devices()
        if monitors:
            print(f"Tous les périphériques Monitor PulseAudio/PipeWire ({len(monitors)} trouvé(s)):")
            print("-" * 80)
            for monitor in monitors:
                hdmi_marker = " [HDMI/DisplayPort]" if monitor.get('is_hdmi', False) else ""
                print(f"[PulseAudio #{monitor['index']}] {monitor['description']}{hdmi_marker}")
                print(f"    Nom: {monitor['name']}")
                # Essayer de mapper vers PyAudio
                pyaudio_index = map_pulseaudio_to_pyaudio(
                    monitor['name'],
                    monitor['description']
                )
                if pyaudio_index is not None:
                    print(f"    → Mappé vers PyAudio index: {pyaudio_index}")
                else:
                    print(f"    → Non accessible via PyAudio directement")
                print()
            print()
        else:
            print("⚠ Aucun Monitor PulseAudio/PipeWire détecté")
            print()

    devices = list_audio_devices()

    print("🎤 Tous les périphériques audio PyAudio disponibles pour capture:")
    print("-" * 80)

    has_input_devices = False
    for device in devices:
        input_channels = device['maxInputChannels']
        if input_channels > 0:
            has_input_devices = True
            # Détecter si c'est probablement un périphérique loopback
            is_loopback = any(
                keyword in device['name'].lower()
                for keyword in ['monitor', 'loopback', 'stereo mix', 'what u hear']
            )
            loopback_marker = " 🔊 [LOOPBACK]" if is_loopback else ""
            print(f"[{device['index']}] {device['name']}{loopback_marker}")
            print(f"    Canaux d'entrée: {input_channels}")
            print(f"    Taux d'échantillonnage: {device['defaultSampleRate']:.0f} Hz")
            print()

    if not has_input_devices:
        print("⚠ Aucun périphérique d'entrée détecté!")
        print()

    # Afficher quel périphérique serait utilisé par défaut
    print("=" * 80)
    print("DÉTECTION AUTOMATIQUE")
    print("=" * 80)
    loopback_index = find_loopback_device()
    if loopback_index is not None:
        device_info = get_device_info(loopback_index)
        if device_info:
            print(f"✓ Périphérique loopback détecté automatiquement:")
            print(f"  Index: {loopback_index}")
            print(f"  Nom: {device_info['name']}")
            print()
            print(f"💡 Pour utiliser ce périphérique:")
            print(f"   uv run python -m src.main")
            print(f"   # OU")
            print(f"   uv run python -m src.main --device {loopback_index}")
    else:
        print("✗ Aucun périphérique de loopback détecté automatiquement")
        print()
        print("📋 Solutions possibles:")
        print()
        if platform.system() == 'Linux':
            print("  1. Vérifier que PulseAudio/PipeWire est en cours d'exécution:")
            print("     pactl info")
            print()
            print("  2. Lister les sources PulseAudio disponibles:")
            print("     pactl list sources short")
            print()
            print("  3. Si aucun Monitor n'est visible, redémarrer PulseAudio/PipeWire:")
            print("     systemctl --user restart pipewire pipewire-pulse")
            print("     # OU")
            print("     pulseaudio --kill && pulseaudio --start")
            print()
            print("  4. Créer un loopback virtuel (temporaire):")
            print("     pactl load-module module-loopback")
        elif platform.system() == 'Windows':
            print("  1. Activer 'Stereo Mix' dans les paramètres audio Windows")
            print("  2. Panneau de configuration → Son → Enregistrement")
            print("  3. Clic droit → Afficher les périphériques désactivés")
            print("  4. Activer 'Stereo Mix' ou 'Mixage stéréo'")
        elif platform.system() == 'Darwin':
            print("  1. Installer BlackHole:")
            print("     brew install blackhole-2ch")
            print()
            print("  2. OU installer Soundflower:")
            print("     brew install soundflower")
        print()
        print("  5. Spécifier manuellement un périphérique:")
        print("     uv run python -m src.main --device INDEX")
        print("     (Choisissez un INDEX dans la liste ci-dessus)")
