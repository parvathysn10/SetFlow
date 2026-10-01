import json
import time
from datetime import datetime
from pathlib import Path

import requests


# These are development seed artists.
# They are NOT the final limit of the SetFlow catalogue.
seed_artists = [
    "Ariana Grande",
    "Don Toliver",
    "The Weeknd",
    "SZA",
    "Travis Scott"
]


url = "https://musicbrainz.org/ws/2/recording/"

headers = {
    "User-Agent": "SetFlow/1.0"
}

raw_folder = Path("data/raw/catalogue")
raw_folder.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def request_musicbrainz(params, max_attempts=3):

    for attempt in range(1, max_attempts + 1):

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10
            )

            print(
                f"Attempt {attempt}: "
                f"status code {response.status_code}"
            )

            if response.status_code == 200:
                return response

        except requests.RequestException as error:
            print(
                f"Attempt {attempt} failed:",
                error
            )

        if attempt < max_attempts:
            print("Waiting before trying again...")
            time.sleep(2)

    return None


for artist in seed_artists:

    print(f"\nExtracting recordings for: {artist}")

    params = {
        "query": f'artist:"{artist}"',
        "fmt": "json",
        "limit": 25,
        "offset": 0
    }

    response = request_musicbrainz(params)

    if response is None:
        print(f"Could not retrieve data for {artist}")
        continue

    data = response.json()

    print(
        f"MusicBrainz reports {data.get('count', 0)} "
        f"matching recordings."
    )

    print(
        f"Downloaded {len(data.get('recordings', []))} "
        f"recordings in this request."
    )

    safe_artist_name = (
        artist.lower()
        .replace(" ", "_")
        .replace(".", "")
    )

    raw_file = raw_folder / (
        f"{safe_artist_name}_{timestamp}.json"
    )

    raw_file.write_text(
        response.text,
        encoding="utf-8"
    )

    print("Raw response saved to:", raw_file)

    # Be polite to the API before requesting the next artist.
    time.sleep(1)


print("\nCatalogue extraction finished.")