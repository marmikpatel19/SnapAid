# app/services/gemini.py

import os
import base64
import json
import uuid
import httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_VISION_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-03-25:generateContent"


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
