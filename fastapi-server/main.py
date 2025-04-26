import json
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class HealthcareFacility(BaseModel):
    name: str
    type: str
    distance: float

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI server!"}

@app.get("/healthcare-facilities", response_model=List[HealthcareFacility])
async def get_healthcare_facilities(
    lat: float = Query(..., description="Latitude of the location"),
    lon: float = Query(..., description="Longitude of the location"),
    limit: int = Query(10, description="Maximum number of facilities to return")
):
    """
    Get healthcare facilities near a given location.
    """
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
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json() 
        print("Response data:", json.dumps(data, indent=2))
        
        facilities = []
        for feature in data.get("features", []):
            attr = feature.get("attributes", {})
            geom = feature.get("geometry")
            if not geom:
                continue
            
            facility_lat = geom.get("y")
            facility_lon = geom.get("x")
            
            # Basic distance approximation
            dist = ((facility_lat - lat)**2 + (facility_lon - lon)**2) ** 0.5
            
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
        nearest_facilities = [
            HealthcareFacility(name=f["name"], type=f["type"], distance=f["distance"])
            for f in facilities[:limit]
        ]
        
        return nearest_facilities
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch healthcare facilities: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 