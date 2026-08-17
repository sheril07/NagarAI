const API_BASE_URL = "http://127.0.0.1:8000";

let mediaRecorder;
let audioChunks = [];

// ---------- Helper: Capture Live GPS Coordinates ----------
function getLiveLocation() {
    const gpsText = document.getElementById("gpsText");
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            if (gpsText) gpsText.innerText = "❌ Not supported by browser";
            reject("Geolocation is not supported by your browser.");
            return;
        }

        if (gpsText) gpsText.innerText = "⌛ Locating...";

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const long = position.coords.longitude;
                if (gpsText) gpsText.innerText = `✅ Active (${lat.toFixed(4)}, ${long.toFixed(4)})`;
                resolve({ lat, long });
            },
            (error) => {
                if (gpsText) gpsText.innerText = "❌ Permission Denied / Error";
                reject("Location permission denied. Please allow location access.");
            }
        );
    });
}

// Check GPS status immediately when page loads
window.addEventListener("DOMContentLoaded", () => {
    getLiveLocation().catch((err) => console.log("Initial GPS check:", err));
});


// ---------- 1A. Voice Complaint: Mic Recording ----------
const startBtn = document.getElementById("startRec");
const stopBtn = document.getElementById("stopRec");
const recStatus = document.getElementById("recStatus");
const statusDiv = document.getElementById("status");

startBtn.addEventListener("click", async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);
        mediaRecorder.start();

        startBtn.disabled = true;
        stopBtn.disabled = false;
        recStatus.innerText = "🔴 Recording... Speak clearly into your mic!";
    } catch (err) {
        alert("Microphone access denied or not supported.");
    }
});

stopBtn.addEventListener("click", () => {
    mediaRecorder.stop();
    recStatus.innerText = "⏳ Processing audio & getting location...";

    mediaRecorder.onstop = async () => {
        startBtn.disabled = false;
        stopBtn.disabled = true;

        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
        const audioFile = new File([audioBlob], "recorded_complaint.webm", { type: "audio/webm" });

        try {
            statusDiv.innerText = "Submitting recorded voice complaint...";
            const coords = await getLiveLocation();

            const formData = new FormData();
            formData.append("file", audioFile);
            formData.append("latitude", coords.lat);
            formData.append("longitude", coords.long);

            const response = await fetch(`${API_BASE_URL}/api/voice-intake`, {
                method: "POST",
                body: formData
            });

            const result = await response.json();
            statusDiv.innerText = "✅ Recorded Voice Submitted!\n\n" + JSON.stringify(result, null, 2);
            recStatus.innerText = "Click Start to record another complaint...";
        } catch (err) {
            statusDiv.innerText = "❌ Error submitting recording: " + err;
            recStatus.innerText = "Recording failed. Try again.";
        }
    };
});


// ---------- 1B. Voice Complaint: File Upload ----------
document.getElementById("voiceForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("audioFile");
    if (!fileInput.files[0]) {
        alert("Please select an audio file first.");
        return;
    }

    try {
        statusDiv.innerText = "Capturing location & uploading audio file...";
        const coords = await getLiveLocation();

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        formData.append("latitude", coords.lat);
        formData.append("longitude", coords.long);

        const response = await fetch(`${API_BASE_URL}/api/voice-intake`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        statusDiv.innerText = "✅ Voice File Submitted!\n\n" + JSON.stringify(result, null, 2);
        fileInput.value = "";
    } catch (err) {
        statusDiv.innerText = "❌ Error submitting voice file: " + err;
    }
});


// ---------- 2. Text Complaint ----------
document.getElementById("textForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const textValue = document.getElementById("textInput").value;

    try {
        statusDiv.innerText = "Capturing location & submitting text complaint...";
        const coords = await getLiveLocation();

        const formData = new FormData();
        formData.append("text", textValue);
        formData.append("latitude", coords.lat);
        formData.append("longitude", coords.long);

        const response = await fetch(`${API_BASE_URL}/api/text-intake`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        statusDiv.innerText = "✅ Text Complaint Submitted!\n\n" + JSON.stringify(result, null, 2);
        document.getElementById("textInput").value = "";
    } catch (err) {
        statusDiv.innerText = "❌ Error submitting text complaint: " + err;
    }
});


// ---------- 3. Image Complaint ----------
document.getElementById("imageForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const imageFile = document.getElementById("imageFile").files[0];
    const caption = document.getElementById("imageCaption").value;

    if (!imageFile) {
        alert("Please select an image file first.");
        return;
    }

    try {
        statusDiv.innerText = "Capturing location & uploading image...";
        const coords = await getLiveLocation();

        const formData = new FormData();
        formData.append("image", imageFile);
        formData.append("caption", caption);
        formData.append("latitude", coords.lat);
        formData.append("longitude", coords.long);

        const response = await fetch(`${API_BASE_URL}/api/image-intake`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        statusDiv.innerText = "✅ Image Complaint Submitted!\n\n" + JSON.stringify(result, null, 2);
        document.getElementById("imageFile").value = "";
        document.getElementById("imageCaption").value = "";
    } catch (err) {
        statusDiv.innerText = "❌ Error submitting image complaint: " + err;
    }
});
