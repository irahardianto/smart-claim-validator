import requests
import base64
import json

# Create a small white 1x1 PNG
dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=")
base64_str = base64.b64encode(dummy_png).decode('utf-8')

url = "http://localhost:8383/run"
payload = {
    "appName": "claim_validator",
    "newMessage": {
        "role": "user",
        "parts": [
            {
                "text": "Check this medical claim.",
                "inlineData": {
                    "mimeType": "image/png",
                    "data": base64_str
                }
            }
        ]
    }
}

print(f"Sending request to {url}...")
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
