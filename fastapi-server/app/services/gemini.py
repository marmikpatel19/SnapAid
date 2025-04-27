import os
from typing import Literal
import base64
import json
import uuid
import httpx
from google import generativeai as genai
from dotenv import load_dotenv
from enum import Enum

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_VISION_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-03-25:generateContent"

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

WorkflowType = Literal["A", "B", "C", "D", "E", "F", "G"]

class Workflow_Prompt(Enum):
    PHYSICAL = """ """
    NONPHYSICAL = """You are to help homeless people get healthcare support. The current user has a non-physical medical issue. 
    Help them solve it. Keep response under 50 tokens!! and no formatting, lists, of parenthesis. response as if you're talking."""

async def determine_workflow(user_prompt: str) -> WorkflowType:
    """
    Use Gemini to determine which workflow to execute based on the user's prompt.
    
    Args:
        user_prompt: The user's input prompt
        
    Returns:
        A single letter indicating the workflow type (A-G)
    """
    model = genai.GenerativeModel('gemini-2.0-flash-001')
    
    prompt = f"""
    You are an orchestration agent for an app to help homeless people get healthcare support.
    Based on the following conversation, decide which of the following categories best fits and return ONLY the corresponding letter:
    
    A: Physical injury (visible wounds, broken bones, etc.)
    B: Internal medical problem (non-physical issues like fever, pain, mental health, etc.)
    C: Resource locator - shelter
    D: Resource locator - pharmacy (any sort of vaccines, purchasing drugs, talking to a pharmacist, etc.)
    E: Resource locator - medical center
    F: Resource locator - washroom
    G: Resource locator - physical resource (clothing, food, etc.)
    
    User prompt: {user_prompt}
    
    Return ONLY the single letter (A-G) that best matches the user's needs.
    """
    
    response = model.generate_content(prompt)
    workflow_type = response.text.strip().upper()
    
    # Validate the response
    if workflow_type not in ["A", "B", "C", "D", "E", "F", "G"]:
        raise ValueError(f"Invalid workflow type returned: {workflow_type}")
    
    return workflow_type 

async def get_general_gemini_response(user_prompt: str, workflow_prompt :Workflow_Prompt) -> str:
    model = genai.GenerativeModel("gemini-2.0-flash-001",)

    prompt = f"""
    {workflow_prompt.value} 
    
    User prompt: {user_prompt}
    """ 
    response = await model.generate_content_async(prompt)
    
    return response.text.strip()

async def send_vision_prompt(prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg"):
    """
    Send a prompt and image to Gemini 2.5 Vision API and return the response text.
    """
    print("Preparing payload for Gemini Vision API...")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    
    session_id = str(uuid.uuid4())
    
    # Encode image to base64
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_image
                        }
                    }
                ]
            }
        ],
        "generation_config": {
            "temperature": 0.4,
            "maxOutputTokens": 1024
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    try:
        print(f"Sending request to Gemini API session={session_id}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GEMINI_VISION_API_URL,
                headers=headers,
                json=payload,
                timeout=30.0
            )

            print(f"Received response status: {response.status_code}")
            if response.status_code != 200:
                error_message = f"Gemini API Error {response.status_code}: {response.text}"
                print(error_message)
                return {"error": error_message}

            response_data = response.json()

            # Extract main response text
            text_response = ""
            if (response_data.get("candidates")
                and len(response_data["candidates"]) > 0
                and response_data["candidates"][0].get("content")
                and response_data["candidates"][0]["content"].get("parts")
                and len(response_data["candidates"][0]["content"]["parts"]) > 0):
                text_response = response_data["candidates"][0]["content"]["parts"][0].get("text", "")
            else:
                print("Warning: Unexpected Gemini API response structure")
                print(json.dumps(response_data, indent=2))

            return {
                "sessionId": session_id,
                "response": text_response,
                "full_response": response_data
            }

    except httpx.RequestError as e:
        print(f"HTTP Request error: {str(e)}")
        return {"error": f"HTTP Request error: {str(e)}"}

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}
