import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google.generativeai import GenerativeModel
import google.generativeai as genai
from google.cloud import storage
import base64
import json
import openai

# Import our custom tool
from modules.tools import get_validation_rules

load_dotenv()

# Configure API Keys
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

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
"status": "APPROVED" | "REJECTED",
"reason": "Explanation of the validation result.",
"data": { "extracted_field": "value", ... }
}
"""

# Tool Schema for OpenAI
GET_VALIDATION_RULES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_validation_rules",
        "description": "Fetch validation rules for a specific claim type from the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "claim_type": {
                    "type": "string",
                    "description": "The type of claim to validate (e.g., 'medical', 'dental', 'vision')."
                }
            },
            "required": ["claim_type"]
        }
    }
}

class GeminiAgent:
    def __init__(self):
        self.model = GenerativeModel("gemini-3-pro-preview")
        self.tools = [get_validation_rules]
        self.chat = self.model.start_chat(
            history=[
                {"role": "user", "parts": [SYSTEM_INSTRUCTIONS]},
                {"role": "model", "parts": ["Understood. I am ready to validate claims."]}
            ],
            enable_automatic_function_calling=True
        )

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
                        "data": part['inlineData']['data']
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

class VLLMAgent:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url=os.getenv("VLLM_API_URL", "http://localhost:8000/v1"),
            api_key=os.getenv("VLLM_API_KEY", "EMPTY")
        )
        # Assuming Qwen 72B is served as the model name, or we can fetch it.
        # Ideally, env var or hardcoded if we know what vLLM is serving.
        # We'll use a generic "model" or try to list it.
        # For now, let's assume the user starts vLLM with a specific model name,
        # but often vLLM endpoints map any model name to the served model if only one is served.
        # Let's use a safe default or env var.
        self.model_name = os.getenv("VLLM_MODEL_NAME", "Qwen/Qwen3-VL-30B-A3B-Instruct") 

    def run(self, new_message):
        """
        Stateless run method for vLLM (OpenAI API).
        Constructs full history for every request.
        """
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTIONS}
        ]

        # Convert ADK input to OpenAI format
        user_content = []
        if 'parts' in new_message:
            for part in new_message['parts']:
                if 'text' in part:
                    user_content.append({"type": "text", "text": part['text']})
                if 'inlineData' in part:
                    # OpenAI expects data URL for images
                    mime = part['inlineData']['mimeType']
                    data = part['inlineData']['data']
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{data}"
                        }
                    })
        
        if user_content:
            messages.append({"role": "user", "content": user_content})

        # First call to model
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=[GET_VALIDATION_RULES_SCHEMA],
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        
        # Check for tool calls
        if response_message.tool_calls:
            # Append model's response to history (it wanted to call a tool)
            messages.append(response_message)
            
            # Execute tools
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "get_validation_rules":
                    logging.info(f"Calling tool {function_name} with {function_args}")
                    tool_result = get_validation_rules(
                        claim_type=function_args.get("claim_type")
                    )
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result),
                    })
            
            # Second call to model with tool results
            final_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            final_text = final_response.choices[0].message.content
        else:
            final_text = response_message.content

        # Wrap in ADK format
        return [
            {
                "content": {
                    "parts": [{"text": final_text}],
                    "role": "model"
                },
                "author": "claim_validator",
                "timestamp": 0
            }
        ]

# Instantiate Agents
gemini_agent = GeminiAgent()
vllm_agent = VLLMAgent()

@app.route('/run', methods=['POST'])
def run_agent():
    """
    Main endpoint used by frontend/client.
    Now mapped to VLLMAgent (Qwen 72B via vLLM).
    """
    data = request.json
    try:
        app_name = data.get('appName')
        new_message = data.get('newMessage')
        
        if not new_message:
             return jsonify({"error": "No message provided"}), 400

        logging.info(f"Received request for {app_name} (routed to VLLMAgent)")
        
        response_events = vllm_agent.run(new_message)
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
    """
    Endpoint for GCS file validation.
    Retains original GeminiAgent logic.
    """
    data = request.json
    try:
        gcs_uri = data.get('gcs_uri')
        mime_type = data.get('mime_type', 'image/png')
        claim_type = data.get('claim_type', 'medical')
        
        if not gcs_uri:
            return jsonify({"error": "Missing gcs_uri"}), 400
            
        logging.info(f"Processing GCS file: {gcs_uri} (routed to GeminiAgent)")
        
        file_bytes = download_gcs_file(gcs_uri)
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
        
        # Use GEMINI AGENT here
        response_events = gemini_agent.run(new_message)
        
        # Post-process for validate-gcs to lift status/reason to top level
        enriched_events = []
        for event in response_events:
            try:
                raw_text = event['content']['parts'][0]['text']
                clean_text = raw_text.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(clean_text)
                
                status = parsed.get("status", "UNKNOWN").upper()
                if status == "VALID": status = "APPROVED"
                if status == "INVALID": status = "REJECTED"
                
                reason = parsed.get("reason", "")
                data_only = {"data": parsed.get("data", {})}
                
                new_event = event.copy()
                new_event['status'] = status
                new_event['status_reason'] = reason
                if 'role' in new_event['content']:
                    del new_event['content']['role']
                
                new_event['content']['parts'][0]['text'] = json.dumps(data_only)
                
                enriched_events.append(new_event)
            except Exception as parse_error:
                logging.warning(f"Failed to parse JSON for GCS response: {parse_error}")
                enriched_events.append(event)

        return jsonify(enriched_events)

    except Exception as e:
        logging.error(f"Error processing GCS request: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8383))
    print(f"ADK Agent Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
