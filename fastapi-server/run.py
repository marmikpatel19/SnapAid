import os

import uvicorn
from pyngrok import ngrok

from app.main import app

# Get port
port = 8000

if __name__ == "__main__":
    # Setup ngrok
    # public_url = ngrok.connect(port).public_url
    # print(f"ngrok tunnel is active at: {public_url}")
    print("Access your FastAPI app at this URL")
    
    # Start the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False) 