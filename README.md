# FastAPI Application

A simple FastAPI application with generic GET and POST endpoints.

## Setup

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run the application:
```
python main.py
```
or
```
uvicorn main:app --reload
```

## Endpoints

- `GET /`: Root endpoint that returns a hello message
- `GET /data`: Returns all data
- `GET /data/{data_id}`: Returns a specific data entry by ID
- `POST /data`: Creates a new data entry

## API Documentation

Once the server is running, you can access:
- Interactive API documentation at: http://localhost:8000/docs
- Alternative API documentation at: http://localhost:8000/redoc 