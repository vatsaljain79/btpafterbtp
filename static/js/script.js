let mediaRecorder;
let isRecording = false;

const recordBtn = document.getElementById('record-btn');
const statusText = document.getElementById('status-text');
const resultCard = document.getElementById('result-card');
const trackTitle = document.getElementById('track-title');
const trackDetails = document.getElementById('track-details');

recordBtn.addEventListener('click', toggleRecording);

async function toggleRecording() {
    if (isRecording) {
        stopRecording();
        statusText.innerText = "Tap to Listen";
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
                channelCount: 1
            }
        });
        mediaRecorder = new MediaRecorder(stream);
        
        let chunks = [];
        let timeElapsed = 0;
        
        mediaRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0 && isRecording) {
                chunks.push(event.data);
                
                // We receive a chunk every 3 seconds
                timeElapsed += 3;
                
                const cumulativeBlob = new Blob(chunks, { type: 'audio/webm' });
                
                // Keep the listening animation going but let the user know we are searching
                statusText.innerText = `Analyzing (${timeElapsed}s)...`;
                
                // Process in the background!
                const matched = await performIdentification(cumulativeBlob);
                
                if (matched) {
                    stopRecording();
                } else if (!matched && timeElapsed >= 21) {
                    // Maximum duration reached and still no match
                    if (isRecording) {
                        stopRecording();
                        statusText.innerText = "Tap to Listen";
                        trackTitle.innerText = "No Match Found";
                        trackDetails.innerText = `Searched 21 seconds. Please try again.`;
                        resultCard.classList.remove('hidden');
                    }
                } else {
                    // We haven't reached 21 seconds, revert text back to Listening...
                    if (isRecording) {
                        statusText.innerText = "Listening...";
                    }
                }
            }
        };

        // Request a data chunk every 3000 milliseconds (3 seconds)
        mediaRecorder.start(3000);
        isRecording = true;
        
        // UI Updates
        recordBtn.classList.add('recording');
        statusText.innerText = "Listening...";
        resultCard.classList.add('hidden');

    } catch (err) {
        console.error("Error accessing microphone:", err);
        alert("Could not access your microphone. Please enable permissions or test from localhost.");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop()); // Release mic
    }
    isRecording = false;
    
    // UI Updates
    recordBtn.classList.remove('recording');
}

async function performIdentification(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'record.webm');

    try {
        const response = await fetch('/api/identify', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        const data = await response.json();
        
        if (data.match) {
            statusText.innerText = "Tap to Listen";
            trackTitle.innerText = data.title;
            trackDetails.innerText = `Score: ${data.score} | Took: ${Math.round(data.time_ms)}ms`;
            resultCard.classList.remove('hidden');
            return true;
        } else {
            return false;
        }
        
    } catch (error) {
        console.error("Error uploading audio:", error);
        return false;
    }
}
