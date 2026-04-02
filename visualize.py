"""
visualize.py
------------
Visualization utilities for the Shazam algorithm.

Generates PNG figures:
  1. Spectrogram (raw STFT magnitude in dB)
  2. Constellation map (spectrogram peaks)
  3. Hash scatter plot (sample time vs database time)
  4. Delta-time histogram (the "match detector")
  5. Recognition-rate vs SNR curve

Usage:
    python visualize.py

All figures are saved to the `figures/` directory.
"""

import os
import numpy as np
import glob

import fingerprint as fp
import database   as db_module
import search     as search_module

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

FIGURES_DIR = "figures"
SAMPLE_RATE = 8000


def ensure_figures():
    os.makedirs(FIGURES_DIR, exist_ok=True)


# ── 1. Spectrogram ──────────────────────────────────────────────────────────

def plot_spectrogram(wav_path, out_path=None):
    if not HAS_MPL:
        print("[SKIP] matplotlib not available")
        return
    samples, sr = fp.load_wav(wav_path)
    spec        = fp.stft_magnitude(samples)
    spec_db     = fp.to_db(spec)

    plt.figure(figsize=(12, 4))
    plt.imshow(spec_db, origin="lower", aspect="auto", cmap="inferno",
               vmin=-80, vmax=0,
               extent=[0, spec.shape[1], 0, sr / 2])
    plt.colorbar(label="dB")
    plt.title(f"Spectrogram — {os.path.basename(wav_path)}")
    plt.xlabel("Time frame")
    plt.ylabel("Frequency (Hz)")
    plt.tight_layout()
    out = out_path or os.path.join(FIGURES_DIR, "spectrogram.png")
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"  Saved: {out}")


# ── 2. Constellation map ────────────────────────────────────────────────────

def plot_constellation(wav_path, out_path=None):
    if not HAS_MPL:
        return
    samples, sr = fp.load_wav(wav_path)
    spec        = fp.stft_magnitude(samples)
    spec_db     = fp.to_db(spec)
    peaks       = fp.get_peaks(spec_db)

    t_peaks = [p[0] for p in peaks]
    f_peaks = [p[1] * (sr / 2) / spec_db.shape[0] for p in peaks]

    plt.figure(figsize=(12, 4))
    plt.scatter(t_peaks, f_peaks, s=4, c="cyan", alpha=0.7)
    plt.title(f"Constellation Map — {os.path.basename(wav_path)}")
    plt.xlabel("Time frame")
    plt.ylabel("Frequency (Hz)")
    plt.gca().set_facecolor("black")
    plt.tight_layout()
    out = out_path or os.path.join(FIGURES_DIR, "constellation.png")
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"  Saved: {out}")


# ── 3 & 4. Scatter plot + histogram (matching vs non-matching) ───────────────

def plot_match_analysis(query_path, song_path, db, meta, out_prefix=None):
    if not HAS_MPL:
        return

    q_hashes  = fp.fingerprint_file(query_path)
    q_hash_set = {h: t for h, t in q_hashes}

    # Find track_id for the matching song
    song_fname = os.path.basename(song_path)
    match_id   = None
    for tid, info in meta.items():
        if info["file"] == song_fname:
            match_id = tid
            break

    # Build delta arrays for the correct match
    correct_deltas = []
    wrong_deltas   = []

    for h_q, t_q in q_hashes:
        if h_q not in db:
            continue
        for tid, t_db in db[h_q]:
            delta = t_db - t_q
            if tid == match_id:
                correct_deltas.append((t_db, t_q, delta))
            else:
                wrong_deltas.append(delta)

    prefix = out_prefix or os.path.join(FIGURES_DIR, "match")

    # ── scatter: matching ──
    if correct_deltas:
        t_dbs   = [x[0] for x in correct_deltas]
        t_smpls = [x[1] for x in correct_deltas]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.scatter(t_dbs, t_smpls, s=12, alpha=0.7)
        ax.set_title("Scatterplot: Matching hash pairs (diagonal present)")
        ax.set_xlabel("Database time frame")
        ax.set_ylabel("Sample time frame")
        fig.tight_layout()
        out = prefix + "_scatter_match.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"  Saved: {out}")

        # ── histogram: matching ──
        deltas = [x[2] for x in correct_deltas]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(deltas, bins=50, color="steelblue", edgecolor="white")
        ax.set_title("Δt Histogram: signals MATCH (sharp peak expected)")
        ax.set_xlabel("Offset t_database − t_sample (frames)")
        ax.set_ylabel("Count")
        fig.tight_layout()
        out = prefix + "_histogram_match.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"  Saved: {out}")

    # ── histogram: non-matching ──
    if wrong_deltas:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(wrong_deltas[:5000], bins=80, color="salmon", edgecolor="white")
        ax.set_title("Δt Histogram: signals do NOT match (flat/noisy)")
        ax.set_xlabel("Offset t_database − t_sample (frames)")
        ax.set_ylabel("Count")
        fig.tight_layout()
        out = prefix + "_histogram_nomatch.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"  Saved: {out}")


# ── 5. Recognition rate vs SNR ──────────────────────────────────────────────

def plot_snr_curve(db, meta, song_path, out_path=None):
    if not HAS_MPL:
        return

    samples, sr = fp.load_wav(song_path)
    n_excerpt   = int(10 * sr)
    mid         = len(samples) // 2
    excerpt     = samples[mid:mid + n_excerpt].copy()
    if len(excerpt) < n_excerpt:
        excerpt = np.pad(excerpt, (0, n_excerpt - len(excerpt)))

    snr_levels  = list(range(-15, 16, 3))
    n_trials    = 5
    correct_pct = []

    song_fname = os.path.basename(song_path)
    match_title = None
    for info in meta.values():
        if info["file"] == song_fname:
            match_title = info["title"]
            break

    print(f"  SNR curve for: {match_title}")
    for snr in snr_levels:
        hits = 0
        for _ in range(n_trials):
            sig_power   = np.mean(excerpt ** 2) + 1e-12
            noise_power = sig_power / (10 ** (snr / 10))
            noisy       = excerpt + np.random.randn(len(excerpt)).astype(np.float32) * np.sqrt(noise_power)
            results     = search_module.identify_samples(noisy, db, meta)
            if results and results[0]["title"].lower() == match_title.lower():
                hits += 1
        pct = 100 * hits / n_trials
        correct_pct.append(pct)
        print(f"    SNR={snr:+3d} dB → {pct:.0f}%")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(snr_levels, correct_pct, "o-", linewidth=2, markersize=7)
    ax.axhline(50, color="gray", linestyle="--", linewidth=1, label="50% line")
    ax.set_title(f"Recognition Rate vs SNR — {match_title}")
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("Recognition Rate (%)")
    ax.set_ylim(-5, 105)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = out_path or os.path.join(FIGURES_DIR, "snr_curve.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"  Saved: {out}")


def main():
    ensure_figures()

    song_files = sorted(glob.glob("songs/*.wav"))
    query_files = sorted(glob.glob("query/query_*.wav"))

    if not song_files:
        print("[ERROR] No songs found. Run generate_songs.py first.")
        return
    if not query_files:
        print("[ERROR] No query files. Run generate_query.py first.")
        return

    song_path  = song_files[0]   # use first song for detailed plots
    query_path = query_files[0]

    print("Loading database...")
    db, meta = db_module.load_database()

    print("\n1. Spectrogram")
    plot_spectrogram(song_path)

    print("\n2. Constellation map")
    plot_constellation(song_path)

    print("\n3 & 4. Match analysis (scatter + histogram)")
    plot_match_analysis(query_path, song_path, db, meta)

    print("\n5. SNR recognition curve (this may take ~30 seconds)")
    plot_snr_curve(db, meta, song_path)

    print("\nAll figures saved to figures/")


if __name__ == "__main__":
    main()
