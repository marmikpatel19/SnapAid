from datetime import datetime, timedelta
import json

import requests
from app.utils.geo import haversine


def get_medical_care_locations(lat, lon, limit):
    """
    Get healthcare facilities near a given location.
    """
    print(f"Getting medical care locations for lat={lat}, lon={lon}, limit={limit}")
    base_url = "https://services.arcgis.com/RmCCgQtiZLDCtblq/ArcGIS/rest/services/CDPH_Healthcare_Facilities/FeatureServer/0/query"
    
    # Create a point geometry with proper spatial reference
    geometry = {
        "x": lon,
        "y": lat,
        "spatialReference": {
            "wkid": 4326,
            "latestWkid": 4326
        }
    }

    params = {
        "f": "json",
        "geometry": json.dumps(geometry),
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "distance": 5000,  # 5km buffer
        "units": "esriSRUnit_Meter",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": True,
        "resultRecordCount": limit,
        "returnDistinctValues": False,
        "returnIdsOnly": False,
        "returnCountOnly": False
    }
    
    try:
        print("Making request to ArcGIS...")
        response = requests.get(base_url, params=params)
        print(f"Response status: {response.status_code}")
        data = response.json()
        print(f"Got {len(data.get('features', []))} features")
        
        facilities = []
        for feature in data.get("features", []):
            attr = feature.get("attributes", {})
            geom = feature.get("geometry")
            if not geom:
                continue
            
            facility_lat = geom.get("y")
            facility_lon = geom.get("x")
            
            # Calculate distance in miles (haversine already returns miles)
            dist = haversine(lon, lat, facility_lon, facility_lat)
            
            # Use the correct field names from the ArcGIS response
            facility_name = attr.get("FACNAME", "Unknown Facility")
            facility_type = attr.get("FAC_FDR", "Unknown Type")
            
            facilities.append({
                "name": facility_name,
                "type": facility_type,
                "distance": dist
            })
        
        # Sort by distance
        facilities.sort(key=lambda x: x["distance"])
        
        # Return only the nearest ones
        result = facilities[:limit]
        print(f"Returning {len(result)} facilities")
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error fetching healthcare facilities: {str(e)}")
        return {"error": f"Failed to fetch healthcare facilities: {str(e)}"}