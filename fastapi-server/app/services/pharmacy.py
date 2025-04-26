from datetime import datetime, timedelta

import requests


def get_easyvax_locations(zip_code, session_id):
    """Query EasyVax API with a zip code and return locations."""
    start_date = datetime.utcnow().replace(hour=7, minute=0, second=0, microsecond=0)
    end_date = (start_date + timedelta(days=1)).replace(hour=6, minute=59, second=59, microsecond=999999)

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'apikey': 'il%I9&*jDCMMocKg',  # API key
        'onramp': 'web',
        'onramp-version': '2.2.1',
        'user-id': session_id,
    }
    
    url = (
        f"https://api.easyvax.com/api/locations"
        f"?campaignId=dtcpdsearch"
        f"&qry={zip_code}"
        f"&serviceCode=COVID"
        f"&vaccineCode=COVID"
        f"&startDate={start_date.isoformat()}Z"
        f"&endDate={end_date.isoformat()}Z"
        f"&radius=20"
    )

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"EasyVax API error: {response.status_code} - {response.text}") 