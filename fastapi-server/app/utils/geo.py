from math import asin, cos, radians, sin, sqrt

from geopy.geocoders import Nominatim


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