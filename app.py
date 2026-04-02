import os
import time
import subprocess
from flask import Flask, request, jsonify, render_template

import database as db_module
import search as search_module

app = Flask(__name__)

# Global variables for db
print("Loading database into memory...")
try:
    global_db, global_meta = db_module.load_database()
    print(f"Loaded {len(global_db)} hashes and {len(global_meta)} tracks.")
except Exception as e:
    print("Database not found or error loading it. Please run `python database.py`.")
    global_db, global_meta = {}, {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/identify", methods=["POST"])
def identify():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400
    
    file = request.files["audio"]
    temp_in = "temp_query_in.webm"
    temp_wav = "temp_query_out.wav"
    
    try:
        file.save(temp_in)
        
        # Convert uploaded file (often webm or ogg) to 8kHz mono 16-bit WAV
        cmd = [
            "ffmpeg", "-y", 
            "-i", temp_in, 
            "-ac", "1", 
            "-ar", "8000", 
            "-acodec", "pcm_s16le", 
            temp_wav
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Identify using Shazam algorithm
        t0 = time.time()
        results = search_module.identify_file(temp_wav, global_db, global_meta, verbose=False)
        elapsed = (time.time() - t0) * 1000
        
        if os.path.exists(temp_in):
            os.remove(temp_in)
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
            
        if results:
            top = results[0]
            # Convert to scalar python types
            return jsonify({
                "match": True,
                "title": top["title"],
                "score": int(top["score"]),
                "offset": int(top["offset"]),
                "time_ms": round(elapsed, 1)
            })
        else:
            return jsonify({
                "match": False,
                "time_ms": round(elapsed, 1)
            })
            
    except Exception as e:
        if os.path.exists(temp_in): os.remove(temp_in)
        if os.path.exists(temp_wav): os.remove(temp_wav)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, ssl_context='adhoc')
