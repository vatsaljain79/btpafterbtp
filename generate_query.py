"""
generate_query.py
-----------------
Creates query audio clips that simulate a real-world Shazam use-case:
  • Takes a short excerpt (default 10 s) from the middle of an existing song
  • Adds Gaussian noise to simulate a microphone / noisy environment
  • Optionally applies a simple frequency-domain EQ shift

Produces:
  query/query_<song_name>.wav  — one query file per song (for batch testing)
  query/demo_query.wav         — a single demo query (Bohemian Rhapsody excerpt)

Usage:
    python generate_query.py
"""

import numpy as np
import wave
import struct
import os
import glob

SONGS_DIR   = "songs"
QUERY_DIR   = "query"
SAMPLE_RATE = 8000

EXCERPT_LEN = 15          # seconds
SNR_DB      = 6           # signal-to-noise ratio in dB for noise addition


def load_wav(path):
    with wave.open(path, "r") as wf:
        raw = wf.readframes(wf.getnframes())
        sr  = wf.getframerate()
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sr


def save_wav(path, samples, sr=SAMPLE_RATE):
    pcm = (np.clip(samples, -1, 1) * 32000).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))


def add_noise(samples, snr_db):
    """Add white Gaussian noise at a specified SNR."""
    sig_power   = np.mean(samples ** 2)
    noise_power = sig_power / (10 ** (snr_db / 10))
    noise       = np.random.randn(len(samples)).astype(np.float32) * np.sqrt(noise_power)
    return samples + noise


def make_query(song_path, out_path, excerpt_len=EXCERPT_LEN, snr_db=SNR_DB):
    samples, sr = load_wav(song_path)

    # Extract the middle portion
    n_excerpt = int(excerpt_len * sr)
    mid       = len(samples) // 2
    start     = max(0, mid - n_excerpt // 2)
    excerpt   = samples[start:start + n_excerpt]

    # Pad if the song is shorter than excerpt_len
    if len(excerpt) < n_excerpt:
        excerpt = np.pad(excerpt, (0, n_excerpt - len(excerpt)))

    noisy = add_noise(excerpt, snr_db)
    save_wav(out_path, noisy, sr)


def main():
    os.makedirs(QUERY_DIR, exist_ok=True)

    song_files = sorted(glob.glob(os.path.join(SONGS_DIR, "*.wav")))
    if not song_files:
        print(f"[ERROR] No songs found in '{SONGS_DIR}/'. Run generate_songs.py first.")
        return

    print(f"Generating {len(song_files)} query clips (10 s excerpt + {SNR_DB} dB SNR noise)...\n")

    for song_path in song_files:
        fname    = os.path.basename(song_path)
        out_name = "query_" + fname
        out_path = os.path.join(QUERY_DIR, out_name)
        print(f"  {fname}  →  {out_name}")
        make_query(song_path, out_path)

    # Also create a single prominent demo query from the first song
    demo_src  = song_files[0]
    demo_path = os.path.join(QUERY_DIR, "demo_query.wav")
    make_query(demo_src, demo_path, snr_db=10)
    print(f"\nDemo query → {demo_path}  (source: {os.path.basename(demo_src)})")
    print("\nDone.")


if __name__ == "__main__":
    main()
