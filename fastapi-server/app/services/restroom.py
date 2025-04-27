import requests


def get_restroom_data():
    """Fetch restroom data from LA Open Data."""
    url = "https://data.lacity.org/resource/s5e6-2pbm.json"  # Public API endpoint
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"LA Restroom API error: {response.status_code} - {response.text}")