from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="My FastAPI App")

# Define a generic data model
class Data(BaseModel):
    id: Optional[str] = None
    content: dict
    metadata: Optional[dict] = None

# In-memory database
data_db = []

@app.get("/")
async def root():
    return {"message": "Hello World, you just pinged the backend api"}

@app.get("/data", response_model=List[Data])
async def get_all_data():
    return data_db

#PIERECE IMPLEMENT UR FIND PHARAMCEIES ENDPOINT HERE
@app.get('/get-pharamacies')
async def get_pharamcies(user_prompt: str) -> Dict:
    pass


@app.post("/data", response_model=Data, status_code=201)
async def create_data(data: Data):
    data_db.append(data)
    return data

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 