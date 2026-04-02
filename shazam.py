"""
shazam.py
---------
Command-line interface for the Shazam implementation.

Usage examples
--------------
# Identify a specific file:
    python shazam.py identify query/demo_query.wav

# Run a full benchmark (all query files vs database):
    python shazam.py benchmark

# Rebuild the database:
    python shazam.py build
"""

import sys
import os
import time

import database as db_module
import search   as search_module
import fingerprint as fp


BANNER = """
╔══════════════════════════════════════════════════════╗
║          🎵  Shazam Algorithm — Wang (2003)  🎵      ║
║    Combinatorial Hash Audio Fingerprinting Engine    ║
╚══════════════════════════════════════════════════════╝
"""


def cmd_build():
    """Build the fingerprint database from songs/."""
    print(BANNER)
    db_module.build_database()


def cmd_identify(query_path, verbose=True):
    """Identify a single query WAV file."""
    print(BANNER)

    if not os.path.exists(query_path):
        print(f"[ERROR] File not found: {query_path}")
        sys.exit(1)

    print(f"Loading database...")
    db, meta = db_module.load_database()
    print(f"  {len(db):,} unique hashes  |  {len(meta)} tracks\n")

    print(f"Fingerprinting query: {query_path}")
    t0      = time.time()
    results = search_module.identify_file(query_path, db, meta, verbose=verbose)
    elapsed = time.time() - t0

    print(f"  Search time: {elapsed*1000:.1f} ms\n")
    _print_results(results)


def cmd_benchmark(query_dir="query", verbose=False):
    """Run all query_*.wav files and report accuracy."""
    print(BANNER)
    import glob

    query_files = sorted(glob.glob(os.path.join(query_dir, "query_*.wav")))
    if not query_files:
        print(f"[ERROR] No query_*.wav files in '{query_dir}/'. Run generate_query.py first.")
        sys.exit(1)

    print(f"Loading database...")
    db, meta = db_module.load_database()
    print(f"  {len(db):,} unique hashes  |  {len(meta)} tracks\n")
    print(f"Running benchmark on {len(query_files)} query clips...\n")
    print(f"  {'Query file':<40} {'Result':<35} {'Score':>6}  {'Time':>8}")
    print("  " + "─" * 95)

    correct = 0
    total   = len(query_files)
    times   = []

    for qpath in query_files:
        qname    = os.path.basename(qpath)
        # expected title = query_Bohemian_Rhapsody.wav → "Bohemian Rhapsody"
        expected = qname.replace("query_", "").replace(".wav", "").replace("_", " ")

        t0      = time.time()
        results = search_module.identify_file(qpath, db, meta, verbose=False)
        elapsed = time.time() - t0
        times.append(elapsed)

        if results:
            top    = results[0]
            match  = top["title"].lower() == expected.lower()
            if match:
                correct += 1
            mark   = "✓" if match else "✗"
            result_str = f"{mark} {top['title']}"
            score  = top["score"]
        else:
            result_str = "✗ No match"
            score      = 0

        print(f"  {qname:<40} {result_str:<35} {score:>6}  {elapsed*1000:>6.1f} ms")

    accuracy = 100 * correct / total
    avg_time = 1000 * sum(times) / len(times)

    print("\n" + "  " + "═" * 95)
    print(f"\n  RESULTS")
    print(f"  ───────────────────────────────")
    print(f"  Correct:  {correct} / {total}")
    print(f"  Accuracy: {accuracy:.1f}%")
    print(f"  Avg time: {avg_time:.1f} ms per query")


def _print_results(results, top_n=5):
    if not results:
        print("  ❌  No match found.")
        return

    top = results[0]
    print(f"  🎵  MATCH FOUND!")
    print(f"      Title : {top['title']}")
    print(f"      Score : {top['score']} matching hash pairs")
    print(f"      Offset: {top['offset']} frames\n")

    if len(results) > 1:
        print(f"  Top {min(top_n, len(results))} candidates:")
        for r in results[:top_n]:
            print(f"    [{r['score']:4d}] {r['title']}")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(BANNER)
        print("Usage:")
        print("  python shazam.py build                 # build database from songs/")
        print("  python shazam.py identify <query.wav>  # identify a single file")
        print("  python shazam.py benchmark             # benchmark all query/ files")
        return

    cmd = args[0]

    if cmd == "build":
        cmd_build()
    elif cmd == "identify":
        if len(args) < 2:
            print("[ERROR] Provide a query WAV path: python shazam.py identify <file.wav>")
            sys.exit(1)
        cmd_identify(args[1])
    elif cmd == "benchmark":
        cmd_benchmark()
    else:
        print(f"[ERROR] Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
