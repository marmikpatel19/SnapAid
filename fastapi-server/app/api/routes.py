import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from app.models.schemas import (
    HealthcareFacility,
    LocationRequest,
    OrchestrationRequest,
    Shelter,
)
from app.services.gemini import Workflow_Prompt, determine_workflow, get_general_gemini_response
from app.services.medical import get_medical_care_locations
from app.services.pharmacy import get_easyvax_locations
from app.services.restroom import get_restroom_data
from app.services.shelter import get_shelter_data
from app.utils.geo import get_zip_from_lat_long, haversine

router = APIRouter(prefix="/api", tags=["api"])

async def handle_physical_injury(latitude: float, longitude: float) -> Dict[str, Any]:
    """Handle physical injury workflow"""
    session_id = str(uuid.uuid4())
    return {
        "sessionId": session_id,
        "message": "stub for physical injury",
        "location": {"latitude": latitude, "longitude": longitude}
    }

async def handle_internal_medical(user_prompt: str) -> str:
    """Handle internal medical problem workflow"""
    session_id = str(uuid.uuid4())
    try:
        response = await get_general_gemini_response(user_prompt, Workflow_Prompt.NONPHYSICAL)
        return {
            "sessionId": session_id,
            "response": response
        }
    except Exception as e:
        return {"sessionId": session_id, "error ": str(e)}

async def handle_pharmacy_request(latitude: float, longitude: float) -> Dict[str, Any]:
    """Handle pharmacy location request"""
    session_id = str(uuid.uuid4())
    try:
        zip_code = get_zip_from_lat_long(latitude, longitude)
        print(f"[handle_pharmacy_request] Zip code: {zip_code}")

        locations = get_easyvax_locations(zip_code, session_id)
        print(f"[handle_pharmacy_request] Locations raw: {locations}")

        if not isinstance(locations, list):
            return {"sessionId": session_id, "error": f"Expected list, got {type(locations).__name__}: {locations}"}

        for loc in locations:
            if loc.get('appointments'):
                has_appointments = any(day['times'] for day in loc['appointments'])
                if has_appointments:
                    pharmacy_info = {
                        "sessionId": session_id,
                        "locationName": loc.get('locationName', 'Unknown'),
                        "address": loc.get('address', 'Unknown'),
                        "city": loc.get('city', 'Unknown'),
                        "state": loc.get('state', 'Unknown'),
                        "zip": loc.get('zip', 'Unknown'),
                        "appointments": [],
                        "distance_miles": loc.get('distance', 0),
                    }
                    for appointment_day in loc['appointments']:
                        if appointment_day.get('times'):
                            day_info = {
                                "date": appointment_day.get('date', 'Unknown'),
                                "times": [slot.get('time', 'Unknown') for slot in appointment_day['times']]
                            }
                            pharmacy_info["appointments"].append(day_info)
                    
                    return pharmacy_info
        
        return {"sessionId": session_id, "message": "No pharmacies with available appointments found."}

    except Exception as e:
        return {"sessionId": session_id, "error": f"Internal error: {str(e)}"}
@router.post("/find_pharmacy")
async def find_pharmacy(req: LocationRequest):
    return await handle_pharmacy_request(req.latitude, req.longitude)

async def handle_restroom_request(latitude: float, longitude: float) -> Dict[str, Any]:
    """Handle restroom location request"""
    session_id = str(uuid.uuid4())

    try:
        user_lat = latitude
        user_lon = longitude
        
        restrooms = get_restroom_data()

        closest_restroom = None
        min_distance = float('inf')

        for restroom in restrooms:
            geom = restroom.get('the_geom')
            if geom and 'coordinates' in geom:
                try:
                    toilets = int(restroom.get('toilets', 0) or 0)
                    urinals = int(restroom.get('urinals', 0) or 0)
                    faucets = int(restroom.get('faucets', 0) or 0)
                except (ValueError, TypeError):
                    toilets = urinals = faucets = 0

                if toilets == 0 and urinals == 0 and faucets == 0:
                    continue

                lon, lat = geom['coordinates']
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
        return {"sessionId": session_id, "error string 2": str(e)}

@router.post("/find_restroom")
async def find_restroom(req: LocationRequest):
    return await handle_restroom_request(req.latitude, req.longitude)
@router.post("/find_healthcare_facilities")
async def find_healthcare_facilities(req: LocationRequest):
    return await handle_medical_center_request(req.latitude, req.longitude)

async def handle_medical_center_request(latitude: float, longitude: float, limit: int = 5) -> Dict[str, Any]:
    """Handle medical center location request"""
    session_id = str(uuid.uuid4())
    try:
        facilities = get_medical_care_locations(latitude, longitude, limit)
        
        if isinstance(facilities, dict) and "error" in facilities:
            return {"sessionId": session_id, "error string 3": facilities["error"]}
        
        return {
            "sessionId": session_id,
            "facilities": facilities
        }
    except Exception as e:
        return {"sessionId": session_id, "error": str(e)}

async def handle_shelter_request(latitude: float, longitude: float) -> Dict[str, Any]:
    """Handle shelter location request"""
    session_id = str(uuid.uuid4())  # Generate fresh session UUID
    try:
        if not latitude or not longitude:
            return {"sessionId": session_id, "error string 4": "Latitude and longitude are required."}
        
        print(f"Latitude: {latitude}, Longitude: {longitude}")
        zip_code = get_zip_from_lat_long(latitude, longitude)
                
        nearest_resource = get_shelter_data(latitude, longitude, zip_code)
        
        return {
            "sessionId": session_id,
            "zipCode": zip_code,
            "nearest_resource": nearest_resource,
            "message": "Found nearest homeless resource."
        }
    
    except Exception as e:
        return {"sessionId": session_id, "error string 5": str(e)}

@router.post("/find_shelter")
async def find_shelter(req: LocationRequest):
    return await handle_shelter_request(req.latitude, req.longitude)

async def handle_physical_resource_request(latitude: float, longitude: float) -> Dict[str, Any]:
    """Handle physical resource location request"""
    session_id = str(uuid.uuid4())
    return {
        "sessionId": session_id,
        "message": "Physical resource location service coming soon.",
        "location": {"latitude": latitude, "longitude": longitude}
    }

@router.post("/orchestrate", response_model=Dict[str, Any])
async def orchestrate(req: OrchestrationRequest):
    """
    Orchestration endpoint that determines which service to call based on semantic similarity.
    
    Args:
        req: Request containing user prompt, location, and optional image
        
    Returns:
        Dictionary with response from the most appropriate service
    """
    try:
        # Determine the workflow using Gemini
        workflow_type = await determine_workflow(req.user_prompt)
        
        # Route to the appropriate service based on workflow type
        if workflow_type == "A":
            return await handle_physical_injury(req.user_prompt)
        elif workflow_type == "B":
            return await handle_internal_medical(req.user_prompt)
        elif workflow_type == "C":
            return await handle_shelter_request(req.latitude, req.longitude)
        elif workflow_type == "D":
            return await handle_pharmacy_request(req.latitude, req.longitude)
        elif workflow_type == "E":
            return await handle_medical_center_request(req.latitude, req.longitude)
        elif workflow_type == "F":
            return await handle_restroom_request(req.latitude, req.longitude)
        elif workflow_type == "G":
            return await handle_physical_resource_request(req.latitude, req.longitude)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
            
    except Exception as e:
        return {"sessionId": str(uuid.uuid4()), "error string 6" : str(e)} 
    
@router.get("/")
async def root():
    return {"message": "Welcome to the FastAPI server!"}