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


from app.services.gemini import send_vision_prompt

@router.post("/vision", response_model=VisionResponseModel)
async def process_vision_request(
    prompt: str = Form(..., description="User text prompt"),
    image: UploadFile = File(..., description="Image of surroundings")
):
    session_id = str(uuid.uuid4())
    try:
        image_content = await image.read()
        mime_type = image.content_type or "image/jpeg"
        
        result = await send_vision_prompt(prompt, image_content, mime_type)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return VisionResponseModel(
            sessionId=result["sessionId"],
            response=result["response"],
            full_response=result["full_response"]
        )

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error processing vision request: {str(e)}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=str(e))


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
