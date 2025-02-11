from pyo import *
 
# List of instrument names used in the UI
INSTRUMENT_NAMES = ["sine", "saw", "square", "samples", "mysynth", "fm", "drumkit"]

def create_instrument(
    instrument,
    freq,
    volume,
    filter_enabled=False,
    filter_frequency=1000,
    selected_sample="bass_synth.wav"
):
    """
    Creates an instrument with a short fade-in/out envelope to avoid clicks.
    Applies a global filter if enabled.

    instrument: one of the names in INSTRUMENT_NAMES
    freq: frequency in Hz
    volume: a float multiplier for loudness (0.0 - 1.0)
    filter_enabled: bool indicating whether to enable the global filter
    filter_frequency: center/cutoff frequency if enabled
    selected_sample: path to the .wav file used for 'samples' instrument

    Returns a tuple [final_output, fader] for controlling/stopping.
    """
    # Short fade envelope
    fader = Fader(fadein=0.02, fadeout=0.1, mul=volume).play()

    if instrument == "sine":
        osc = Sine(freq=freq)
    elif instrument == "saw":
        osc = SuperSaw(freq=freq)
    elif instrument == "square":
        osc = LFO(freq=freq, type=2)  # type=2 => square wave
    elif instrument == "samples":
        # Plays an external .wav sample
        osc = SfPlayer(f"samples/{selected_sample}", speed=1, loop=True)
        # Optionally add pitch shifting
        osc = Harmonizer(osc, transpo=0.5)
    elif instrument == "mysynth":
        # Complex synthesis with modulation + noise
        base_osc = RCOsc(freq=freq, sharp=0.8)
        mod = Sine(freq=freq * 0.5, mul=0.2)
        noise = PinkNoise(mul=0.1)
        osc = base_osc + mod + noise
        # Additional bandpass filtering for character
        osc = Biquad(osc, freq=freq, q=1.2, type=1)
    elif instrument == "fm":
        ratio_val = freq / 200.0
        osc = FM(carrier=freq, ratio=ratio_val, index=10)
    elif instrument == "drumkit":
        # Example: freq < 100 => Kick, < 200 => Snare, else => Hi-Hat
        if freq < 100:  # Kick
            kick = Sine(freq=freq, mul=volume).mix(2)
            kick_env = Adsr(attack=0.01, decay=0.15, sustain=0, release=0.1, mul=volume).play()
            osc = kick * kick_env
        elif freq < 200:  # Snare
            noise = PinkNoise(mul=volume * 0.5)
            snare_env = Adsr(attack=0.01, decay=0.2, sustain=0, release=0.1, mul=volume).play()
            osc = Biquad(noise, freq=2000, q=0.8, type=1) * snare_env
        else:  # Hi-Hat
            noise = PinkNoise(mul=volume * 0.3)
            hat_env = Adsr(attack=0.01, decay=0.05, sustain=0, release=0.02, mul=volume).play()
            osc = Biquad(noise, freq=8000, q=1.0, type=1) * hat_env
    else:
        # Default fallback
        osc = Sine(freq=freq)

    source = osc * fader

    # Optionally route through a global filter
    if filter_enabled:
        source = Biquad(source, freq=filter_frequency, type=0)  # lowpass

    return [source, fader]
