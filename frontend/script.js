const API_BASE_URL = "http://127.0.0.1:8000";

// Helper function to capture live GPS coordinates
function getLiveLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject("Geolocation is not supported by your browser.");
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    lat: position.coords.latitude,
                    long: position.coords.longitude
                });
            },
            (error) => {
                reject("Location permission denied. Please allow location access.");
            }
        );
    });
}

// Handle Voice Submission
document.getElementById("voiceForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusDiv = document.getElementById("status");
    const fileInput = document.getElementById("audioFile");

    if (!fileInput.files[0]) return;

    try {
        statusDiv.innerText = "Capturing location and submitting voice...";
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
        statusDiv.innerText = "Success: " + JSON.stringify(result, null, 2);
    } catch (err) {
        statusDiv.innerText = "Error: " + err;
    }
});

// Handle Text Submission
document.getElementById("textForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusDiv = document.getElementById("status");
    const textValue = document.getElementById("textInput").value;

    try {
        statusDiv.innerText = "Capturing location and submitting text...";
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
        statusDiv.innerText = "Success: " + JSON.stringify(result, null, 2);
    } catch (err) {
        statusDiv.innerText = "Error: " + err;
    }
});
