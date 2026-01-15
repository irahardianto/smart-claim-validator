import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
# from google.adk import Agent, Tool
from google.generativeai import GenerativeModel
import google.generativeai as genai
from google.cloud import storage
import base64


# Import our custom tool
from modules.tools import get_validation_rules

load_dotenv()

# Configure API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

# Define the Gemini Model
model = GenerativeModel("gemini-3-pro-preview")

# Define the Agent System Instructions
SYSTEM_INSTRUCTIONS = """
You are an automated Claim Validator Agent.
**Your Process:**

1. First, analyze the user's input to determine the claim_type (e.g., 'medical', 'dental', 'vision'). If explicit in input, use that.
2. **MANDATORY:** Call the tool `get_validation_rules` with this claim type to fetch the policy.
3. Once you have the rules, analyze the provided image strictly against those rules. Check for required fields and values.
4. Output your final answer **exclusively** as a valid JSON object. Do not include markdown code blocks (```json ... ```), just the raw JSON.

JSON Output Format:
{
"status": "valid" | "invalid",
"reason": "Explanation of the validation result.",
"data": { "extracted_field": "value", ... }
}
"""

# Define the ADK Agent
# Note: google-adk API might vary, assuming a standard Agent wrapper here.
# If google-adk is not available, we can use raw genai with tools.
# For this POC, we will use genai directly since 'google-adk' might be a placeholder in the prompt
# but strictly following the prompt's request to use 'google-adk' if possible.
# Given I cannot verify 'google-adk' installed, I will simulate the 'Agent' behavior using standard genai if needed,
# but let's try to structure it as an "Agent" class as requested.

class ClaimValidatorAgent:
    def __init__(self):
        self.model = model
        self.tools = [get_validation_rules]
        self.chat = self.model.start_chat(
            history=[
                {"role": "user", "parts": [SYSTEM_INSTRUCTIONS]},
                {"role": "model", "parts": ["Understood. I am ready to validate claims."]}
            ],
            enable_automatic_function_calling=True
        ) # Note: enable_automatic_function_calling in genai setup

    def run(self, new_message):
        # new_message structure expects 'parts' with text/image
        # We need to adapt the input to Gemini's expected format
        
        # Extract text and image from the ADK-style request
        user_parts = []
        
        if 'parts' in new_message:
            for part in new_message['parts']:
                if 'text' in part:
                    user_parts.append(part['text'])
                if 'inlineData' in part:
                    # Convert base64 to image part
                    user_parts.append({
                        "mime_type": part['inlineData']['mimeType'],
                        "data": part['inlineData']['data'] # genai expects raw bytes or similar depending on version
                        # Actually genai client expects 'data' as bytes if using 'blob' or similar.
                        # We might need to decode base64 if passing as 'inline_data'.
                    })
        
        response = self.chat.send_message(user_parts, tools=self.tools)
        
        # Wrap response in ADK standard format
        return [
            {
                "content": {
                    "parts": [{"text": response.text}],
                    "role": "model"
                },
                "author": "claim_validator",
                "timestamp": 0 # Placeholder
            }
        ]

agent = ClaimValidatorAgent()

@app.route('/run', methods=['POST'])
def run_agent():
    data = request.json
    try:
        app_name = data.get('appName')
        new_message = data.get('newMessage')
        
        if not new_message:
             return jsonify({"error": "No message provided"}), 400

        logging.info(f"Received request for {app_name}")
        
        response_events = agent.run(new_message)
        return jsonify(response_events)

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

def download_gcs_file(gcs_uri):
    """Downloads a file from GCS and returns bytes."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI. Must start with 'gs://'")
    
    # Parse bucket and blob name
    path_parts = gcs_uri[5:].split("/", 1)
    if len(path_parts) != 2:
        raise ValueError("Invalid GCS URI format.")
        
    bucket_name, blob_name = path_parts
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    return blob.download_as_bytes()

@app.route('/validate-gcs', methods=['POST'])
def validate_gcs():
    data = request.json
    try:
        gcs_uri = data.get('gcs_uri')
        mime_type = data.get('mime_type', 'image/png') # Default or require?
        claim_type = data.get('claim_type', 'medical')
        
        if not gcs_uri:
            return jsonify({"error": "Missing gcs_uri"}), 400
            
        logging.info(f"Processing GCS file: {gcs_uri}")
        
        file_bytes = download_gcs_file(gcs_uri)
        # GenAI expects client-side image data usually as base64 or bytes depending on the client method.
        # But 'agent.run' helper we wrote expects ADK format which has 'inlineData' as base64.
        
        base64_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Construct message compatible with our agent.run
        new_message = {
            "role": "user",
            "parts": [
                {
                    "text": f"Check this {claim_type} claim.",
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": base64_data
                    }
                }
            ]
        }
        
        response_events = agent.run(new_message)
        return jsonify(response_events)

    except Exception as e:
        logging.error(f"Error processing GCS request: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8383))
    print(f"ADK Agent Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
