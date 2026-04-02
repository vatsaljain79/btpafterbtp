"""
database.py
-----------
Build and persist the fingerprint database.

The database is a Python dict (saved as a .pkl file):
    {
        hash32: [(track_id, time_frame), ...],
        ...
    }

A companion metadata dict maps track_id → {"title": ..., "artist": ...}.

Usage:
    python database.py          # builds database from songs/ directory
"""

import os
import pickle
import time

import fingerprint as fp

DB_PATH   = "database/fingerprints.pkl"
META_PATH = "database/metadata.pkl"
SONGS_DIR = "songs"


def build_database(songs_dir=SONGS_DIR, db_path=DB_PATH, meta_path=META_PATH):
    """Fingerprint every .wav in songs_dir and save the database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    db   = {}          # hash32 → [(track_id, time_frame), ...]
    meta = {}          # track_id → {"title": ..., "artist": ...}

    wav_files = sorted(
        f for f in os.listdir(songs_dir) if f.lower().endswith(".wav")
    )

    if not wav_files:
        print(f"[ERROR] No .wav files found in '{songs_dir}/'")
        return

    print(f"Building database from {len(wav_files)} songs...\n")

    for track_id, fname in enumerate(wav_files):
        path  = os.path.join(songs_dir, fname)
        title = fname.replace("_", " ").replace(".wav", "")

        t0 = time.time()
        hashes = fp.fingerprint_file(path)
        elapsed = time.time() - t0

        meta[track_id] = {"title": title, "file": fname}

        for h, t_frame in hashes:
            db.setdefault(h, []).append((track_id, t_frame))

        print(f"  [{track_id:02d}] {title}")
        print(f"        {len(hashes):,} hashes  |  {elapsed:.2f}s")

    print(f"\nTotal unique hashes: {len(db):,}")
    print(f"Total tracks:        {len(meta)}")

    with open(db_path, "wb") as f:
        pickle.dump(db, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(meta_path, "wb") as f:
        pickle.dump(meta, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"\nDatabase saved → {db_path}")
    print(f"Metadata saved → {meta_path}")
    return db, meta


def load_database(db_path=DB_PATH, meta_path=META_PATH):
    """Load a previously built database from disk."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database not found at '{db_path}'. Run `python database.py` first."
        )
    with open(db_path, "rb") as f:
        db = pickle.load(f)
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)
    return db, meta


if __name__ == "__main__":
    build_database()
