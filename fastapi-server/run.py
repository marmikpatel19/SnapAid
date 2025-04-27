import uvicorn
from pyngrok import ngrok

if __name__ == "__main__":
    # Start ngrok tunnel
    port = 8000
    public_url = ngrok.connect(port).public_url
    print(f"ngrok tunnel created at: {public_url}")
    print(f"Open this URL in your browser to access your FastAPI server")
    
    # Start FastAPI server
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        reload=True,
        log_level="debug"
    )
