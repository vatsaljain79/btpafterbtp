# ShazamPy - Web Interface

## Overview
ShazamPy now includes a fully functional, real-time web application! Instead of using the command line to identify songs, you can simply run the web server, open your browser, and tap a button to record audio directly from your microphone. 

## Features
- **Progressive Detection**: The web UI records your microphone and smartly evaluates the audio in the background every 5 seconds (up to 20 seconds). It stops recording instantly as soon as a match is found.
- **Secure Microphone Support**: Captures audio seamlessly using your browser's native `MediaRecorder` API.
- **HTTPS Enabled**: The Flask app uses an *adhoc* SSL context, ensuring your connection is treated as secure. This is required by modern browsers to allow microphone permissions and allows you to test the app from your mobile phone on the same Wi-Fi.
- **Sleek UI**: Fast, responsive, dark-mode glassmorphic interface built with Vanilla CSS and JS.

## Prerequisites
Before running the web app, ensure you have built the core audio database so the backend has songs to match against.

```bash
# 1. Download songs and build the database (if you haven't already):
python generate_songs.py
python database.py

# 2. Install Web dependencies:
pip install Flask pyOpenSSL cryptography
```

## How to Run

1. Start the Flask web server in your terminal:
   ```bash
   python app.py
   ```
2. The server will launch a real-time secure API and web client on **port 5000**.
3. Open your browser and navigate to:
   ```
   https://127.0.0.1:5000
   ```
   *(To use your phone's microphone, connect to the same Wi-Fi and navigate to your computer's local IP Address, e.g., `https://192.168.1.X:5000`)*

4. **Bypass the Privacy Warning**: Because the app automatically generates a local development SSL certificate to secure the microphone connection, your browser will warn you that the "connection is not private". 
   - Click **Advanced**
   - Click **Proceed to ... (unsafe)**
5. Tap the pulsating **Listen** button on the UI, grant microphone permissions when prompted, and start identifying songs!