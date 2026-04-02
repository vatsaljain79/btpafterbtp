"""
generate_songs.py (Downloader version)
-----------------
Downloads popular Bollywood songs from YouTube and converts them to 8kHz Mono WAV.
Each song is clipped to 30 seconds.

Usage:
    python generate_songs.py
"""

import yt_dlp
import os
import subprocess
import glob

OUTPUT_DIR = "songs"
SAMPLE_RATE = 8000
DURATION = 30

# 50 Bollywood songs to download
SONGS = [
    # Initial 20
    ("Tum Hi Ho", "ytsearch1:Tum Hi Ho Arijit Singh audio"),
    ("Chaiyya Chaiyya", "ytsearch1:Chaiyya Chaiyya audio"),
    ("Kal Ho Naa Ho", "ytsearch1:Kal Ho Naa Ho title track audio"),
    ("Agar Tum Saath Ho", "ytsearch1:Agar Tum Saath Ho audio"),
    ("Desi Girl", "ytsearch1:Desi Girl Dostana audio"),
    ("Jai Ho", "ytsearch1:Jai Ho Slumdog Millionaire audio"),
    ("Kabira", "ytsearch1:Kabira Yeh Jawaani Hai Deewani audio"),
    ("Senorita", "ytsearch1:Senorita Zindagi Na Milegi Dobara audio"),
    ("Ghungroo", "ytsearch1:Ghungroo War audio"),
    ("Mitwa", "ytsearch1:Mitwa Kabhi Alvida Naa Kehna audio"),
    ("Chaleya", "ytsearch1:Chaleya Jawan audio"),
    ("Gerua", "ytsearch1:Gerua audio"),
    ("Tujh Mein Rab Dikhta Hai", "ytsearch1:Tujh Mein Rab Dikhta Hai audio"),
    ("Dheere Dheere", "ytsearch1:Dheere Dheere Se Meri Zindagi audio"),
    ("Kar Gayi Chull", "ytsearch1:Kar Gayi Chull audio"),
    ("Kala Chashma", "ytsearch1:Kala Chashma audio"),
    ("Sheila Ki Jawani", "ytsearch1:Sheila Ki Jawani audio"),
    ("Ilahi", "ytsearch1:Ilahi YJHD audio"),
    ("Zinda", "ytsearch1:Zinda Bhaag Milkha Bhaag audio"),
    ("Tere Bina", "ytsearch1:Tere Bina Guru audio"),
    # Additional 30
    ("Chammak Challo", "ytsearch1:Chammak Challo audio"),
    ("Dil Diyan Gallan", "ytsearch1:Dil Diyan Gallan audio"),
    ("Raabta", "ytsearch1:Raabta title track audio"),
    ("Samjhawan", "ytsearch1:Samjhawan audio"),
    ("Munni Badnaam Hui", "ytsearch1:Munni Badnaam Hui audio"),
    ("Balam Pichkari", "ytsearch1:Balam Pichkari audio"),
    ("Sooraj Dooba Hain", "ytsearch1:Sooraj Dooba Hain audio"),
    ("Ae Dil Hai Mushkil", "ytsearch1:Ae Dil Hai Mushkil title song audio"),
    ("Jhoome Jo Pathaan", "ytsearch1:Jhoome Jo Pathaan audio"),
    ("Bom Diggy Diggy", "ytsearch1:Bom Diggy Diggy audio"),
    ("Aankh Marey", "ytsearch1:Aankh Marey Simmba audio"),
    ("Naina", "ytsearch1:Naina Dangal audio"),
    ("Kun Faya Kun", "ytsearch1:Kun Faya Kun audio"),
    ("Tera Ban Jaunga", "ytsearch1:Tera Ban Jaunga audio"),
    ("Bekhayali", "ytsearch1:Bekhayali Kabir Singh audio"),
    ("Badtameez Dil", "ytsearch1:Badtameez Dil audio"),
    ("Tum Se Hi", "ytsearch1:Tum Se Hi Jab We Met audio"),
    ("Hawayein", "ytsearch1:Hawayein Jab Harry Met Sejal audio"),
    ("Apna Time Aayega", "ytsearch1:Apna Time Aayega audio"),
    ("Kesariya", "ytsearch1:Kesariya audio"),
    ("Apna Bana Le", "ytsearch1:Apna Bana Le Bhediya audio"),
    ("Param Sundari", "ytsearch1:Param Sundari audio"),
    ("Raataan Lambiyan", "ytsearch1:Raataan Lambiyan audio"),
    ("Lungi Dance", "ytsearch1:Lungi Dance audio"),
    ("Genda Phool", "ytsearch1:Genda Phool Badshah audio"),
    ("Aapka Kya Hoga Janabe Ali", "ytsearch1:Aapka Kya Hoga Janabe Ali audio"),
    ("Galliyan", "ytsearch1:Galliyan Ek Villain audio"),
    ("Zaalima", "ytsearch1:Zaalima Raees audio"),
    ("Tamma Tamma Again", "ytsearch1:Tamma Tamma Again audio"),
    ("Kajra Re", "ytsearch1:Kajra Re Bunty Aur Babli audio")
]

def safe_filename(title):
    return title.replace(" ", "_").replace("'", "").replace(".", "") + ".wav"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Downloading {len(SONGS)} Bollywood songs...\n")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }

    for title, query in SONGS:
        out_wav = os.path.join(OUTPUT_DIR, safe_filename(title))
        
        # Skip if already downloaded
        if os.path.exists(out_wav):
            print(f"  Already exists: {title}. Skipping...")
            continue
            
        print(f"  Downloading & Converting: {title}...")
        
        safe_title = title.replace(" ", "")
        ydl_opts['outtmpl'] = f"temp_{safe_title}.%(ext)s"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(query, download=True)
                
            temp_files = glob.glob(f"temp_{safe_title}.*")
            if not temp_files:
                print(f"    [Error] Could not find downloaded file for {title}")
                continue
                
            temp_file = temp_files[0]
            
            cmd = [
                "ffmpeg", "-y", 
                "-i", temp_file,
                "-t", str(120),
                "-ac", "1", 
                "-ar", str(SAMPLE_RATE), 
                "-acodec", "pcm_s16le",
                out_wav
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
        except Exception as e:
            print(f"    [Error] Failed to process {title}: {e}")
            
    print("\nDone. Songs downloaded and converted.")

if __name__ == "__main__":
    main()
