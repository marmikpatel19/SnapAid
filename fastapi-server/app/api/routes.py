from typing import List
import uuid

from fastapi import APIRouter, Depends, Query

from app.models.schemas import HealthcareFacility, LocationRequest
from app.services.pharmacy import get_easyvax_locations
from app.services.restroom import get_restroom_data
from app.services.medical import get_medical_care_locations
from app.utils.geo import get_zip_from_lat_long, haversine

from typing import Optional
import base64
from pydantic import BaseModel
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import httpx
import json

router = APIRouter(prefix="/api", tags=["API Endpoints"])
from typing import Optional
import base64
from pydantic import BaseModel
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import httpx
import json

# Create a router for vision API endpoints
vision_router = APIRouter(prefix="/api", tags=["Vision API"])

# Define the request model
class VisionResponseModel(BaseModel):
    sessionId: str
    response: str
    full_response: Optional[dict] = None

import os

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY environment variable is not set")
    
GEMINI_VISION_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-03-25:generateContent"

@router.post("/vision", response_model=VisionResponseModel)
async def process_vision_request(
    prompt: str = Form(..., description="User text prompt"),
    image: UploadFile = File(..., description="Image of surroundings")
):
    session_id = str(uuid.uuid4())
    
    try:
        # Read and encode image
        image_content = await image.read()
        mime_type = image.content_type or "image/jpeg"
        base64_image = base64.b64encode(image_content).decode("utf-8")
        
        # Log key information for debugging
        print(f"Session ID: {session_id}")
        print(f"Image size: {len(image_content)} bytes")
        print(f"MIME type: {mime_type}")
        print(f"Prompt length: {len(prompt)} characters")
        
        # Prepare request payload for Gemini
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
        
        # Set up API request headers
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
            
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        # Make request to Gemini API
        print(f"Making request to Gemini API: {GEMINI_VISION_API_URL}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    GEMINI_VISION_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                print(f"API Response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_message = f"Gemini API error: Status {response.status_code}, Response: {response.text}"
                    print(error_message)
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_message
                    )
                
                response_data = response.json()
                
                # Extract the text response
                text_response = ""
                if (response_data.get("candidates") 
                    and len(response_data["candidates"]) > 0 
                    and response_data["candidates"][0].get("content") 
                    and response_data["candidates"][0]["content"].get("parts")
                    and len(response_data["candidates"][0]["content"]["parts"]) > 0):
                    text_response = response_data["candidates"][0]["content"]["parts"][0].get("text", "")
                else:
                    print("Warning: Unexpected response structure from Gemini API")
                    print(f"Response data: {json.dumps(response_data, indent=2)}")
                
                return VisionResponseModel(
                    sessionId=session_id,
                    response=text_response,
                    full_response=response_data
                )
            except httpx.RequestError as exc:
                error_message = f"HTTP Request error: {str(exc)}"
                print(error_message)
                raise HTTPException(status_code=500, detail=error_message)
            
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message = f"Error processing vision request: {str(e)}\n\nTraceback: {error_traceback}"
        print(error_message)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing vision request: {str(e)}"
        )


@router.post("/find_pharmacy")
async def find_pharmacy(req: LocationRequest):
    session_id = str(uuid.uuid4())  # Generate fresh session UUID
    try:
        print(f"Received request to find pharmacy for session {session_id}")
        print(f"Request details: {req}")
        if not req.latitude or not req.longitude:
            return {"sessionId": session_id, "error": "Latitude and longitude are required."}
        print(f"Latitude: {req.latitude}, Longitude: {req.longitude}")
        # Convert latitude and longitude to zip code
        print("Converting latitude and longitude to zip code...")
        print(f"Latitude: {req.latitude}, Longitude: {req.longitude}")
        print(f"Session ID: {session_id}")
        zip_code = get_zip_from_lat_long(req.latitude, req.longitude)
        locations = get_easyvax_locations(zip_code, session_id)
        
        for loc in locations:
            # Check if the location has appointments available      
            if loc.get('appointments'):
                has_appointments = any(day['times'] for day in loc['appointments'])
                if has_appointments:
                    pharmacy_info = {
                        "sessionId": session_id,
                        "locationName": loc['locationName'],
                        "address": loc['address'],
                        "city": loc['city'],
                        "state": loc['state'],
                        "zip": loc['zip'],
                        "appointments": [],
                        "distance_miles": loc.get('distance', 0),
                    }
                    
                    for appointment_day in loc['appointments']:
                        if appointment_day['times']:
                            day_info = {
                                "date": appointment_day['date'],
                                "times": [slot['time'] for slot in appointment_day['times']]
                            }
                            pharmacy_info["appointments"].append(day_info)
                    
                    return pharmacy_info
        
        return {"sessionId": session_id, "message": "No pharmacies with available appointments found."}
    
    except Exception as e:
        return {"sessionId": session_id, "error": str(e)}

@router.post("/find_restroom")
async def find_restroom(req: LocationRequest):
    session_id = str(uuid.uuid4())  # Generate fresh session UUID
    try:
        user_lat = req.latitude
        user_lon = req.longitude
        
        restrooms = get_restroom_data()

        closest_restroom = None
        min_distance = float('inf')

        for restroom in restrooms:
            geom = restroom.get('the_geom')
            if geom and 'coordinates' in geom:
                # Get counts and safely convert to integers
                try:
                    toilets = int(restroom.get('toilets', 0) or 0)
                    urinals = int(restroom.get('urinals', 0) or 0)
                    faucets = int(restroom.get('faucets', 0) or 0)
                except (ValueError, TypeError):
                    # If values are not numbers, treat them as 0
                    toilets = urinals = faucets = 0

                # Skip restroom if all are zero
                if toilets == 0 and urinals == 0 and faucets == 0:
                    continue

                lon, lat = geom['coordinates']  # GeoJSON format: [longitude, latitude]
                distance = haversine(user_lon, user_lat, lon, lat)

                if distance < min_distance:
                    min_distance = distance
                    closest_restroom = {
                        "facility": restroom.get('facility', 'Unknown'),
                        "gender": restroom.get('gender', 'Unknown'),
                        "toilets": toilets,
                        "urinals": urinals,
                        "faucets": faucets,
                        "location": geom,
                        "distance_miles": round(distance, 2)
                    }

        if closest_restroom:
            return {
                "sessionId": session_id,
                "nearestRestroom": closest_restroom
            }
        else:
            return {
                "sessionId": session_id,
                "message": "No restrooms found."
            }

    except Exception as e:
        return {"sessionId": session_id, "error": str(e)}


@router.get("/healthcare-facilities", response_model=List[HealthcareFacility])
async def get_healthcare_facilities(
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    limit: int = Query(10, description="Maximum number of facilities to return")
):
    try:
        facilities = get_medical_care_locations(lat, lon, limit)
        
        if isinstance(facilities, dict) and "error" in facilities:
            return {"error": facilities["error"]}
        
        return [HealthcareFacility(name=f["name"], type=f["type"], distance=f["distance"]) for f in facilities]
    
    except Exception as e:
        return {"error": str(e)}

@router.get("/")
async def root():
    return {"message": "Welcome to the FastAPI server!"}
