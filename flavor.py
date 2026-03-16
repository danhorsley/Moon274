import random
import math
import pygame
import struct

# ── Peake-inspired flavor text ──────────────────────────────────────

HEIST_FLAVOR = [
    "Horns sprouting after that deal? Check your reflection.",
    "The stolen goods hum with a frequency that makes your teeth ache.",
    "Somewhere, a rival curator weeps into their ledger.",
    "The cargo bay smells of ozone and regret.",
    "Your crew grins. The kind of grin that precedes indictments.",
]

TRADE_FLAVOR = [
    "Goods change hands under Saturn's amber glow.",
    "The deal is sealed with a handshake and a frequency modulation.",
    "Credits flow like light through a prism — splitting, refracting.",
    "A fair exchange. The Variance barely notices.",
    "The trader's eyes are old. Older than the rings.",
]

PROTECT_FLAVOR = [
    "Moon 274's shields hum a lullaby of paranoia.",
    "The defense grid flickers — a constellation of caution.",
    "Safe, for now. But safety is a borrowed coat.",
    "Your walls thicken. So does the silence.",
    "Fortified. The universe notes your preference for stillness.",
]

TOURIST_ARRIVAL = [
    "A visitor descends through the ring-shadow. They carry strange cargo.",
    "The emissary's shuttle leaves frost patterns on the landing pad.",
    "Customs flags something unnameable in the tourist's luggage.",
    "They arrive smelling of distant moons and unfinished equations.",
    "The docking clamps engage. Something shifts in the station's hum.",
]

GOLDEN_AGE_FLAVOR = [
    "The labs burn bright. Researchers forget to sleep, then forget to eat.",
    "Breakthroughs cascade like dominoes made of light.",
    "The knowledge lattice sings — a chord that hasn't been heard in centuries.",
    "Every screen shows something new. Most of it terrifying.",
    "Progress. The beautiful, ravenous engine.",
]

EQUILIBRIUM_WARN = [
    "Your wings itch. That's the Variance talking.",
    "The station's lights flicker in a pattern that looks like counting down.",
    "Something in the walls is whispering probabilities.",
    "The air tastes of static. The meter is watching.",
    "Every surface reflects a slightly different version of you.",
]

RIVAL_HEIST_FLAVOR = [
    "Alarms across the sector. Someone's been busy.",
    "A distant moon goes dark. Then bright. Then dark again.",
    "The comms crackle with accusations in three languages.",
    "Honor among thieves is a currency that's been devalued.",
]

IDLE_FLAVOR = [
    "Saturn turns. The rings whisper their ancient arithmetic.",
    "A quiet tick. The kind that precedes storms.",
    "The station creaks. Metal remembering it was once ore.",
    "Somewhere, a probability collapses into certainty.",
    "The void stares back. It has excellent eye contact.",
    "Dust motes drift past the viewport like tiny resigned planets.",
]

GAME_OVER_FLAVOR = {
    "negative": [
        "The Variance swallows Moon 274 whole. You taste equations.",
        "Reintegration is painless. That's the worst part.",
        "Your atoms rejoin the probability cloud. You were always just a pattern.",
    ],
    "positive": [
        "Perfect balance achieved. You are preserved in amber harmony. Forever.",
        "The crystal lattice of order encloses you. Beautiful. Eternal. Done.",
        "You have become the equilibrium. The equilibrium has no need for you.",
    ],
}


def get_flavor(category):
    """Return a random flavor line from a category."""
    pools = {
        "heist": HEIST_FLAVOR,
        "trade": TRADE_FLAVOR,
        "protect": PROTECT_FLAVOR,
        "tourist": TOURIST_ARRIVAL,
        "golden_age": GOLDEN_AGE_FLAVOR,
        "equilibrium_warn": EQUILIBRIUM_WARN,
        "rival_heist": RIVAL_HEIST_FLAVOR,
        "idle": IDLE_FLAVOR,
    }
    pool = pools.get(category, IDLE_FLAVOR)
    return random.choice(pool)


def get_game_over_flavor(negative=True):
    key = "negative" if negative else "positive"
    return random.choice(GAME_OVER_FLAVOR[key])


# ── Sound generation (pure Pygame, no external files) ───────────────

def _generate_tone(frequency, duration_ms, volume=0.3, sample_rate=22050):
    """Generate a sine wave tone as a Pygame Sound object."""
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        # Fade envelope
        env = min(1.0, min(i, n_samples - i) / (sample_rate * 0.02))
        val = int(32767 * volume * env * math.sin(2 * math.pi * frequency * t))
        # 16-bit signed stereo
        sample = struct.pack('<hh', val, val)
        buf.extend(sample)
    sound = pygame.mixer.Sound(buffer=bytes(buf))
    return sound


def _generate_noise_burst(duration_ms, volume=0.15, sample_rate=22050):
    """Generate a filtered noise burst."""
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytearray()
    prev = 0
    for i in range(n_samples):
        env = min(1.0, min(i, n_samples - i) / (sample_rate * 0.01))
        raw = random.uniform(-1, 1)
        # Simple low-pass
        filtered = prev * 0.7 + raw * 0.3
        prev = filtered
        val = int(32767 * volume * env * filtered)
        sample = struct.pack('<hh', val, val)
        buf.extend(sample)
    return pygame.mixer.Sound(buffer=bytes(buf))


class SoundBank:
    """Pre-generated sound effects."""
    def __init__(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception:
            self.enabled = False
            return

        self.sounds = {
            "tick":         _generate_tone(220, 40, 0.1),
            "command":      _generate_tone(440, 80, 0.2),
            "heist":        _generate_noise_burst(150, 0.25),
            "trade":        _generate_tone(330, 120, 0.15),
            "protect":      _generate_tone(550, 100, 0.15),
            "golden_age":   _generate_tone(660, 300, 0.3),
            "warning":      _generate_tone(180, 200, 0.25),
            "game_over":    _generate_tone(110, 800, 0.4),
            "tourist":      _generate_tone(495, 150, 0.15),
        }

    def play(self, name):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()
