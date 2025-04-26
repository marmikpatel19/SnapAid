from typing import List
import uuid

from fastapi import APIRouter, Depends, Query

from app.models.schemas import HealthcareFacility, LocationRequest
from app.services.pharmacy import get_easyvax_locations
from app.services.restroom import get_restroom_data
from app.utils.geo import get_zip_from_lat_long, haversine
from app.services.medical import get_medical_care_locations

router = APIRouter(prefix="/api", tags=["api"])

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

@router.get("/healthcare-facilities", response_model=List[HealthcareFacility])
async def get_healthcare_facilities(
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    limit: int = Query(10, description="Maximum number of facilities to return")
):
    facilities = get_medical_care_locations(lat, lon, limit)
    
    if isinstance(facilities, dict) and "error" in facilities:
        return {"error": facilities["error"]}
    
    # Convert to HealthcareFacility objects
    return [HealthcareFacility(name=f["name"], type=f["type"], distance=f["distance"]) for f in facilities]

@router.get("/")
async def root():
    return {"message": "Welcome to the FastAPI server!"} 