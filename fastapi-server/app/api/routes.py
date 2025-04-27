from typing import List
import uuid

from fastapi import APIRouter, Depends, Query

from app.models.schemas import HealthcareFacility, LocationRequest
from app.services.pharmacy import get_easyvax_locations
from app.services.restroom import get_restroom_data
from app.services.medical import get_medical_care_locations
from app.utils.geo import get_zip_from_lat_long, haversine
from app.services.gemini import determine_workflow

router = APIRouter(prefix="/api", tags=["api"])

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
    facilities = get_medical_care_locations(lat, lon, limit)
    
    if isinstance(facilities, dict) and "error" in facilities:
        return {"error": facilities["error"]}
    
    # Convert to HealthcareFacility objects
    return [HealthcareFacility(name=f["name"], type=f["type"], distance=f["distance"]) for f in facilities]

@router.post("/find_shelter")
async def find_shelter(req: LocationRequest):
    session_id = str(uuid.uuid4())  # Generate fresh session UUID
    try:
        user_lat = req.latitude
        user_lon = req.longitude
        
        shelters = get_shelter_data()

        nearest_shelters = []
        for shelter in shelters:
            # Check if shelter has location data
            if shelter.get('latitude') and shelter.get('longitude'):
                shelter_lat = float(shelter.get('latitude'))
                shelter_lon = float(shelter.get('longitude'))
                
                # Calculate distance using haversine formula
                distance = haversine(user_lon, user_lat, shelter_lon, shelter_lat)
                
                shelter_info = {
                    "name": shelter.get('shelter_name', 'Unknown'),
                    "address": shelter.get('address', 'Unknown'),
                    "phone": shelter.get('contact_number', 'Unknown'),
                    "hours": shelter.get('hours', 'Unknown'),
                    "service_type": shelter.get('service_type', 'Unknown'),
                    "distance_miles": round(distance, 2),
                    "latitude": shelter_lat,
                    "longitude": shelter_lon
                }
                
                nearest_shelters.append(shelter_info)
        
        # Sort shelters by distance
        nearest_shelters.sort(key=lambda x: x['distance_miles'])
        
        # Return top 5 nearest shelters
        if nearest_shelters:
            return {
                "sessionId": session_id,
                "nearestShelters": nearest_shelters[:5]
            }
        else:
            return {
                "sessionId": session_id,
                "message": "No shelters found."
            }
            
    except Exception as e:
        return {"sessionId": session_id, "error": str(e)}

@router.get("/shelters", response_model=List[Shelter])
async def get_shelters(
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    limit: int = Query(5, description="Maximum number of shelters to return")
):
    try:
        shelters_data = get_shelter_data()
        
        shelter_list = []
        for shelter in shelters_data:
            if shelter.get('latitude') and shelter.get('longitude'):
                shelter_lat = float(shelter.get('latitude'))
                shelter_lon = float(shelter.get('longitude'))
                
                # Calculate distance
                distance = haversine(lon, lat, shelter_lon, shelter_lat)
                
                shelter_list.append(Shelter(
                    name=shelter.get('shelter_name', 'Unknown Shelter'),
                    address=shelter.get('address', 'Unknown Address'),
                    phone=shelter.get('contact_number', 'Unknown'),
                    distance=distance,
                    latitude=shelter_lat,
                    longitude=shelter_lon
                ))
        
        # Sort by distance and limit results
        shelter_list.sort(key=lambda x: x.distance)
        return shelter_list[:limit]
        
    except Exception as e:
        return {"error": f"Failed to fetch shelters: {str(e)}"}

@router.get("/")
async def root():
    return {"message": "Welcome to the FastAPI server!"}

@router.post("/orchestrate", response_model=Dict[str, Any])
async def orchestrate(req: OrchestrationRequest):
    """
    Orchestration endpoint that determines which service to call based on semantic similarity.
    
    Args:
        req: Request containing user prompt, location, and optional image
        
    Returns:
        Dictionary with response from the most appropriate service
    """
    session_id = str(uuid.uuid4())
    
    try:
        # Determine the workflow using Gemini
        workflow_type = await determine_workflow(req.user_prompt)
        
        # Create location request for the appropriate service
        location_req = LocationRequest(
            latitude=req.latitude,
            longitude=req.longitude
        )
        
        # Route to the appropriate service based on workflow type
        if workflow_type == "A":
            print("stub for physical injury")
            # Physical injury - route to image processing
            return;
        elif workflow_type == "B":
            # Internal medical problem - route conversation
            print("stub for non-physical concern")
            return;
        elif workflow_type == "C":
            # Shelter locator
            return await find_shelter(location_req)
        elif workflow_type == "D":
            # Pharmacy locator
            return await find_pharmacy(location_req)
        elif workflow_type == "E":
            # Medical center locator
            return await get_healthcare_facilities(
                lat=req.latitude,
                lon=req.longitude,
                limit=5
            )
        elif workflow_type == "F":
            # Washroom locator
            return await find_restroom(location_req)
        elif workflow_type == "G":
            # Physical resource locator - for now, return a message
            return {
                "sessionId": session_id,
                "message": "Physical resource location service coming soon."
            }
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
            
    except Exception as e:
        return {
            "sessionId": session_id,
            "error": str(e)
        } 