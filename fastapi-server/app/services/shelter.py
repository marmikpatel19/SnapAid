import requests
from bs4 import BeautifulSoup
from app.utils.geo import haversine  # assuming you already have this

def get_shelter_data(user_lat, user_lon, zip_code):
    """Fetch and return the closest homeless resource to the user location."""
    
    url = "https://www.lapl.org/homeless-resources"
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': f'https://www.lapl.org/homeless-resources?distance%5Bpostal_code%5D={zip_code}&distance%5Bsearch_distance%5D=2&distance%5Bsearch_units%5D=mile',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
    }

    params = {
        'distance[postal_code]': zip_code,
        'distance[search_distance]': str(20),
        'distance[search_units]': 'mile',
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"LAPL Homeless Resources fetch error {response.status_code}: {response.text}")

    soup = BeautifulSoup(response.text, 'html.parser')
    
    resources = []
    all_entries = soup.find_all('li', class_='views-row')

    for entry in all_entries:
        name_tag = entry.find('h3')
        address_phone_tag = entry.find('p', class_='hrc')
        map_link_tag = entry.find('a', class_='show-map-link')
        
        if name_tag and address_phone_tag and map_link_tag:
            name = name_tag.get_text(strip=True)
            full_text = address_phone_tag.get_text(strip=True)
            if "|" in full_text:
                address, phone = [part.strip() for part in full_text.split("|", 1)]
            else:
                address, phone = full_text, "Unknown"
            
            latitude = map_link_tag['data-latitude']
            longitude = map_link_tag['data-longitude']

            # Calculate distance from user to shelter
            dist = haversine(user_lon, user_lat, float(longitude), float(latitude))

            resources.append({
                "name": name,
                "address": address,
                "phone": phone,
                "latitude": latitude,
                "longitude": longitude,
                "distance_miles": dist
            })

    # Sort by distance
    resources.sort(key=lambda x: x["distance_miles"])

    # Return the nearest shelter (first one)
    if resources:
        return resources[0]
    else:
        return {"error": "No homeless resources found."}
