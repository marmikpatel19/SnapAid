from datetime import datetime, timedelta

import requests


def get_easyvax_locations(zip_code: str, session_id: str):
    """Query EasyVax API with a zip code and session ID, and return available locations."""
    
    # Set the start and end times (7:00 AM today to 6:59:59 AM tomorrow, UTC)
    start_date = datetime.utcnow().replace(hour=7, minute=0, second=0, microsecond=0)
    end_date = (start_date + timedelta(days=1)).replace(hour=6, minute=59, second=59, microsecond=999999)

    # Prepare request headers
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'apikey': 'il%I9&*jDCMMocKg',
        'onramp': 'web',
        'onramp-version': '2.2.1',
        'origin': 'https://www.easyvax.com',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
        'user-id': session_id,
    }

    # Build the API URL
    url = (
        f"https://api.easyvax.com/api/locations"
        f"?campaignId=0"
        f"&qry={zip_code}"
        f"&serviceCode=COVID"
        f"&vaccineCode=COVID"
        f"&startDate={start_date.isoformat()}Z"
        f"&endDate={end_date.isoformat()}Z"
        f"&radius=20"
    )

    # Make the GET request
    response = requests.get(url, headers=headers)
    print(response.json)
    print(response.status_code)
    try:
        response.raise_for_status()
        print(response.json)
        print(response.status_code)
    except requests.HTTPError as e:
        print(response.json)
        print(response.status_code)
        print(f"[get_easyvax_locations] HTTP Error: {e}")
        print(f"[get_easyvax_locations] Raw response: {response.text}")
        raise

    try:
        data = response.json()
        print(response.json)
        print(response.status_code)
        print(f"[get_easyvax_locations] JSON decoded successfully.")
        return data
    except Exception as e:
        print(response.json)
        print(response.status_code)
        print(f"[get_easyvax_locations] Failed to decode JSON: {e}")
        print(f"[get_easyvax_locations] Raw response text: {response.text}")
        raise ValueError(f"Failed to decode JSON: {e}")

