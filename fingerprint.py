"""
fingerprint.py
--------------
Core audio fingerprinting module implementing the Wang (2003) algorithm.

Pipeline:
  1. Load WAV → mono float32 array
  2. Compute spectrogram (STFT magnitude)
  3. Extract constellation map (local spectrogram peaks)
  4. Generate combinatorial hashes from anchor→target-zone pairs
  5. Return list of (hash32, time_offset) tuples
"""

import numpy as np
import wave
import struct
from scipy.ndimage import maximum_filter


# ── STFT / spectrogram parameters ──────────────────────────────────────────
FFT_WINDOW_SIZE  = 4096          # samples per FFT window
FFT_HOP_SIZE     = 512           # hop between windows
SAMPLE_RATE      = 8000          # Hz

# ── Constellation / peak parameters ────────────────────────────────────────
PEAK_NEIGHBORHOOD = 20           # radius for local-max filter (time×freq bins)
MIN_AMPLITUDE_DB  = -60          # ignore bins below this dB level
MAX_PEAKS_PER_SEC = 15           # density cap

# ── Hash parameters (target zone) ──────────────────────────────────────────
FAN_OUT          = 10            # max pairs per anchor point
TARGET_T_MIN     = 1             # target zone: min time distance from anchor
TARGET_T_MAX     = 20            # target zone: max time distance from anchor
TARGET_F_MIN     = -100          # target zone: freq bin range (relative to anchor)
TARGET_F_MAX     = 100


# ── I/O helpers ────────────────────────────────────────────────────────────

def load_wav(path):
    """Read a mono 16-bit WAV file; return (samples, sample_rate)."""
    with wave.open(path, "r") as wf:
        n_frames   = wf.getnframes()
        sr         = wf.getframerate()
        n_channels = wf.getnchannels()
        raw        = wf.readframes(n_frames)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if n_channels == 2:                          # stereo → mono
        samples = samples.reshape(-1, 2).mean(axis=1)
    samples /= 32768.0                           # normalise to [-1, 1]
    return samples, sr


# ── Spectrogram ─────────────────────────────────────────────────────────────

def stft_magnitude(samples, window_size=FFT_WINDOW_SIZE, hop_size=FFT_HOP_SIZE):
    """Short-time Fourier transform magnitude (one-sided)."""
    window = np.hanning(window_size)
    n_frames = 1 + (len(samples) - window_size) // hop_size
    spec = np.zeros((window_size // 2 + 1, n_frames), dtype=np.float32)
    for i in range(n_frames):
        start  = i * hop_size
        frame  = samples[start:start + window_size]
        if len(frame) < window_size:
            frame = np.pad(frame, (0, window_size - len(frame)))
        spectrum  = np.fft.rfft(frame * window)
        spec[:, i] = np.abs(spectrum).astype(np.float32)
    return spec                   # shape: (freq_bins, time_frames)


def to_db(spec, ref=1.0, amin=1e-10):
    return 20 * np.log10(np.maximum(amin, spec) / ref)


# ── Constellation map ───────────────────────────────────────────────────────

def get_peaks(spec_db, neighborhood=PEAK_NEIGHBORHOOD,
              min_db=MIN_AMPLITUDE_DB, max_peaks_per_sec=MAX_PEAKS_PER_SEC,
              hop_size=FFT_HOP_SIZE, sr=SAMPLE_RATE):
    """
    Find local maxima in the dB spectrogram.
    Returns list of (time_frame, freq_bin) tuples.
    """
    struct  = np.ones((neighborhood, neighborhood), dtype=bool)
    local_max = maximum_filter(spec_db, footprint=struct) == spec_db
    above_min = spec_db > min_db
    peaks_mask = local_max & above_min

    freq_idxs, time_idxs = np.where(peaks_mask)
    amps = spec_db[freq_idxs, time_idxs]

    # Sort by amplitude descending, then thin by density
    order = np.argsort(-amps)
    freq_idxs = freq_idxs[order]
    time_idxs = time_idxs[order]
    amps      = amps[order]

    # Density cap: keep at most max_peaks_per_sec peaks per second
    frames_per_sec = sr / hop_size
    n_time_frames  = spec_db.shape[1]
    n_time_secs    = n_time_frames / frames_per_sec
    max_peaks      = int(n_time_secs * max_peaks_per_sec)

    peaks = list(zip(time_idxs[:max_peaks], freq_idxs[:max_peaks]))
    peaks.sort(key=lambda p: p[0])   # sort by time
    return peaks


# ── Combinatorial hashing ──────────────────────────────────────────────────

def _make_hash(f1, f2, dt):
    """Pack (f1, f2, Δt) into a 32-bit integer."""
    # f1: 10 bits, f2: 10 bits, dt: 12 bits  → 32 bits total
    f1  = int(f1)  & 0x3FF          # 10 bits
    f2  = int(f2)  & 0x3FF          # 10 bits
    dt  = int(dt)  & 0xFFF          # 12 bits
    return (f1 << 22) | (f2 << 12) | dt


def generate_hashes(peaks,
                    fan_out=FAN_OUT,
                    t_min=TARGET_T_MIN, t_max=TARGET_T_MAX,
                    f_min=TARGET_F_MIN, f_max=TARGET_F_MAX):
    """
    Given a list of (time_frame, freq_bin) peaks,
    return a list of (hash32, anchor_time_frame) tuples.
    """
    hashes = []
    n = len(peaks)
    for i, (t1, f1) in enumerate(peaks):
        count = 0
        for j in range(i + 1, n):
            t2, f2 = peaks[j]
            dt = t2 - t1
            if dt < t_min:
                continue
            if dt > t_max:
                break
            df = f2 - f1
            if f_min <= df <= f_max:
                h = _make_hash(f1, f2, dt)
                hashes.append((h, t1))
                count += 1
                if count >= fan_out:
                    break
    return hashes


# ── Public API ──────────────────────────────────────────────────────────────

def fingerprint_file(path):
    """
    Full pipeline: WAV file → list of (hash32, time_frame) tuples.
    """
    samples, sr = load_wav(path)
    spec        = stft_magnitude(samples)
    spec_db     = to_db(spec)
    peaks       = get_peaks(spec_db)
    hashes      = generate_hashes(peaks)
    return hashes


def fingerprint_samples(samples, sr=SAMPLE_RATE):
    """
    Same pipeline but accepts a raw numpy array (e.g. a noisy excerpt).
    """
    spec    = stft_magnitude(samples)
    spec_db = to_db(spec)
    peaks   = get_peaks(spec_db)
    hashes  = generate_hashes(peaks)
    return hashes
