from pydantic import BaseModel


class LocationRequest(BaseModel):
    latitude: float
    longitude: float 

class HealthcareFacility(BaseModel):
    name: str
    type: str
    distance: float

class Shelter(BaseModel):
    name: str
    address: str
    phone: str
    distance: float
    latitude: float
    longitude: float

class OrchestrationRequest(BaseModel):
    user_prompt: str
    latitude: float
    longitude: float
    image_surroundings: str = None  # Base64 encoded image