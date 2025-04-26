from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import uuid
import json
from pydantic import BaseModel
from math import radians, cos, sin, asin, sqrt


app = FastAPI()
# Define the body schema for POST request
class LocationRequest(BaseModel):
    latitude: float
    longitude: float

def haversine(lon1, lat1, lon2, lat2):
    """Calculate the great-circle distance between two points (in miles)."""
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 3956  # Radius of Earth in miles
    return c * r

def get_zip_from_lat_long(lat, long):
    """Get zip code from latitude and longitude using Nominatim."""
    geolocator = Nominatim(user_agent="easyvax_locator")
    location = geolocator.reverse((lat, long), exactly_one=True)
    if location and 'postcode' in location.raw['address']:
        return location.raw['address']['postcode']
    else:
        raise ValueError("Zip code could not be found for the given coordinates.")

def get_easyvax_locations(zip_code, session_id):
    """Query EasyVax API with a zip code and return locations."""
    start_date = datetime.utcnow().replace(hour=7, minute=0, second=0, microsecond=0)
    end_date = (start_date + timedelta(days=1)).replace(hour=6, minute=59, second=59, microsecond=999999)

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'apikey': 'il%I9&*jDCMMocKg',  # your provided API key
        'onramp': 'web',
        'onramp-version': '2.2.1',
        'user-id': session_id,
    }
    
    url = (
        f"https://api.easyvax.com/api/locations"
        f"?campaignId=dtcpdsearch"
        f"&qry={zip_code}"
        f"&serviceCode=COVID"
        f"&vaccineCode=COVID"
        f"&startDate={start_date.isoformat()}Z"
        f"&endDate={end_date.isoformat()}Z"
        f"&radius=20"
    )

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"EasyVax API error: {response.status_code} - {response.text}")

@app.post("/find_pharmacy")
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

def get_restroom_data():
    """Fetch restroom data from LA Open Data."""
    url = "https://data.lacity.org/resource/s5e6-2pbm.json"  # Public API endpoint
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"LA Restroom API error: {response.status_code} - {response.text}")

@app.post("/find_restroom")
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
#test
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
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI server!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 