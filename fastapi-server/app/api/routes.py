import uuid
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.schemas import LocationRequest
from app.services.pharmacy import get_easyvax_locations
from app.services.restroom import get_restroom_data
from app.utils.geo import get_zip_from_lat_long, haversine

router = APIRouter()

AVAILABLE_SERVICES = ['restroom', 'pharmacy']

# Simple enum for query types
class QueryType(Enum):
    PHARMACY = "pharmacy"
    RESTROOM = "restroom"
    UNKNOWN = "unknown"

# Simple schema for the orchestration endpoint
class UserPrompt(BaseModel):
    prompt: str
    latitude: float
    longitude: float


def determine_intent(prompt: str) -> QueryType:
    """
    Determine the intent of the user prompt.
    This is a simple placeholder for an LLM-based approach.
    """
    prompt_lower = prompt.lower()
    
    # Pharmacy/vaccine related keywords
    pharmacy_keywords = [
        'pharmacy', 'pharmacies', 'medicine', 'prescription', 'drug', 
        'vaccine', 'vaccination', 'shot', 'immunization', 'booster',
        'covid', 'flu', 'pills', 'medication'
    ]
    
    # Restroom related keywords
    restroom_keywords = [
        'restroom', 'bathroom', 'toilet', 'lavatory', 'washroom', 
        'facilities', 'wc', 'water closet', 'urinal', 'latrine'
    ]
    
    # Check for pharmacy-related query
    if any(keyword in prompt_lower for keyword in pharmacy_keywords):
        return QueryType.PHARMACY
    
    # Check for restroom-related query
    if any(keyword in prompt_lower for keyword in restroom_keywords):
        return QueryType.RESTROOM
    
    # Default if unable to determine
    return QueryType.UNKNOWN

@router.post("/orchestrate")
async def orchestrate_query(req: UserPrompt):
    """
    Endpoint that receives natural language queries and routes to appropriate services.
    This can be extended to use a proper LLM in the future.
    """
    session_id = str(uuid.uuid4())
    
    # Check if we have coordinates
    if req.latitude is None or req.longitude is None:
        return {
            "sessionId": session_id,
            "message": "Coordinates are required. Please provide latitude and longitude.",
            "requiredInput": ["latitude", "longitude"]
        }
    
    # Create location request with the coordinat
    
    location_req = LocationRequest(latitude=req.latitude, longitude=req.longitude)
    
    # Determine intent from the prompt
    query_type = determine_intent(req.prompt)
    
    # Route to appropriate endpoint based on detected intent
    if query_type == QueryType.PHARMACY:
        result = await find_pharmacy(location_req)
        return {
            "sessionId": session_id,
            "queryType": "pharmacy",
            "result": result
        }
    elif query_type == QueryType.RESTROOM:
        result = await find_restroom(location_req)
        return {
            "sessionId": session_id,
            "queryType": "restroom",
            "result": result
        }
    else:
        return {
            "sessionId": session_id,
            "message": "Could not determine intent from your query. Please try being more specific or use direct endpoints.",
            "availableServices": AVAILABLE_SERVICES
        }

@router.post("/find_pharmacy")
async def find_pharmacy(req: LocationRequest):
    session_id = str(uuid.uuid4())  # Generate fresh session UUID
    try:
        zip_code = get_zip_from_lat_long(req.latitude, req.longitude)
        
        locations = get_easyvax_locations(zip_code, session_id)
        
        for loc in locations:
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
                lon, lat = geom['coordinates']  # GeoJSON format: [longitude, latitude]
                distance = haversine(user_lon, user_lat, lon, lat)

                if distance < min_distance:
                    min_distance = distance
                    closest_restroom = {
                        "facility": restroom.get('facility', 'Unknown'),
                        "gender": restroom.get('gender', 'Unknown'),
                        "toilets": restroom.get('toilets', 'Unknown'),
                        "urinals": restroom.get('urinals', 'Unknown'),
                        "faucets": restroom.get('faucets', 'Unknown'),
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
        
@router.get("/")
async def root():
    return {"message": "Welcome to the FastAPI server!"} 


#create a mock call to call the orchestrate endpoint
if __name__ == '__main__':
    sample_data = {
        
    }
