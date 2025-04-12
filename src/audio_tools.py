from pydub.generators import Sine
from pydub import AudioSegment

AUDIO_FADE_MS = 5 # Fade in/out for clicks
AUDIO_SAMPLE_RATE = 44100 # Hz

def create_tone(frequency, duration_ms):
    """Generates a sine wave tone AudioSegment."""
    return Sine(frequency).to_audio_segment(
        duration=duration_ms, volume=-10 # Use -10 dB volume
    ).fade_in(AUDIO_FADE_MS).fade_out(AUDIO_FADE_MS)

def create_silence(duration_ms):
    """Generates silence AudioSegment."""
    return AudioSegment.silent(duration=duration_ms, frame_rate=AUDIO_SAMPLE_RATE)
