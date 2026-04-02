"""
search.py
---------
Given a query audio excerpt, identify which database track it came from.

Algorithm (Wang 2003 §2.3):
  1. Fingerprint the query → list of (hash, t_sample)
  2. Look up each hash in the database → candidate (track_id, t_db) pairs
  3. For each track, compute Δt = t_db − t_sample for every matching pair
  4. Histogram the Δt values; a sharp peak means the track aligns perfectly
  5. The score = height of the tallest histogram peak
  6. Return the track with the highest score (if above threshold)
"""

import numpy as np
from collections import defaultdict
import fingerprint as fp


SCORE_THRESHOLD = 5    # minimum matching hash pairs to call it a match


def search(query_hashes, db, meta, threshold=SCORE_THRESHOLD, verbose=False):
    """
    Match query_hashes against the database.

    Parameters
    ----------
    query_hashes : list of (hash32, time_frame)
    db           : fingerprint database dict
    meta         : track metadata dict
    threshold    : minimum score to report a match

    Returns
    -------
    list of dicts sorted by score descending:
        [{"track_id": int, "title": str, "score": int, "offset": int}, ...]
    """
    # --- collect time-pair candidates per track ---
    # candidates[track_id] = list of (t_db - t_sample) deltas
    candidates = defaultdict(list)

    for h_query, t_sample in query_hashes:
        if h_query not in db:
            continue
        for track_id, t_db in db[h_query]:
            delta = t_db - t_sample
            candidates[track_id].append(delta)

    if verbose:
        print(f"  Matched hashes into {len(candidates)} candidate tracks")

    # --- score each candidate via delta-histogram peak ---
    results = []
    for track_id, deltas in candidates.items():
        if len(deltas) < threshold:
            continue

        deltas_arr = np.array(deltas)

        # Histogram with 1-frame bins
        lo, hi = int(deltas_arr.min()), int(deltas_arr.max()) + 1
        if lo == hi:
            peak_score = len(deltas)
            best_offset = lo
        else:
            hist, edges = np.histogram(deltas_arr, bins=range(lo, hi + 1))
            peak_score  = int(hist.max())
            best_offset = int(edges[hist.argmax()])

        if peak_score >= threshold:
            results.append({
                "track_id": track_id,
                "title":    meta[track_id]["title"],
                "file":     meta[track_id]["file"],
                "score":    peak_score,
                "offset":   best_offset,
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def identify_file(query_path, db, meta, verbose=False):
    """Identify a WAV file against the database. Returns sorted result list."""
    hashes = fp.fingerprint_file(query_path)
    if verbose:
        print(f"  Query fingerprint: {len(hashes):,} hashes")
    return search(hashes, db, meta, verbose=verbose)


def identify_samples(samples, db, meta, verbose=False):
    """Identify a raw numpy samples array against the database."""
    hashes = fp.fingerprint_samples(samples)
    if verbose:
        print(f"  Query fingerprint: {len(hashes):,} hashes")
    return search(hashes, db, meta, verbose=verbose)
