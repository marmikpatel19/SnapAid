from pydantic import BaseModel


class LocationRequest(BaseModel):
    latitude: float
    longitude: float 

class HealthcareFacility(BaseModel):
    name: str
    type: str
    distance: float