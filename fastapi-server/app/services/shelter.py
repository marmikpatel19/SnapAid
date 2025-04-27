import json

import requests


def get_shelter_data():
    """Fetch shelter data from LA Open Data."""
    url = "https://data.lacity.org/resource/84hx-i9ij.json"  # LA Winter Shelter Program API endpoint
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"LA Shelter API error: {response.status_code} - {response.text}") 