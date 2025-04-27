from math import asin, cos, radians, sin, sqrt
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError

def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate the great-circle distance between two points on Earth (in miles)."""
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 3956  # Radius of Earth in miles
    return c * r
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
import requests

POSITIONSTACK_API_KEY = "YOUR_POSITIONSTACK_API_KEY"  # <<< Replace with your actual API key

def get_zip_from_lat_long(lat: float, lon: float) -> str:
    """Get ZIP code from latitude and longitude using PositionStack API."""
    url = "http://api.positionstack.com/v1/reverse"
    params = {
        'access_key': "12bc86edb96acc806a5a4404eeee2988",
        'query': f"{lat},{lon}",
        'limit': 1
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['data']:
            location = data['data'][0]
            if 'postal_code' in location and location['postal_code']:
                return location['postal_code']
            else:
                raise ValueError("Zip code could not be found in the response.")
        else:
            raise ValueError("No location data found for given coordinates.")
    else:
        raise ConnectionError(f"PositionStack API error {response.status_code}: {response.text}")
