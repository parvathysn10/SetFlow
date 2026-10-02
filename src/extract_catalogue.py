import time
from datetime import datetime
from pathlib import Path

import requests


# Development seed artists chosen to give SetFlow a broader
# musical catalogue. These are catalogue seeds, not genre labels:
# individual artists and recordings can span multiple styles.
seed_artists = [
    # Existing catalogue
    "Ariana Grande",
    "Don Toliver",
    "The Weeknd",
    "SZA",
    "Travis Scott",

    # Broader contemporary pop / dance
    "Dua Lipa",
    "Lady Gaga",
    "Calvin Harris",

    # Electronic / dance
    "Daft Punk",
    "Disclosure",

    # Indie / alternative
    "Arctic Monkeys",
    "Tame Impala",

    # Rock
    "Foo Fighters",
    "Fleetwood Mac",

    # Country
    "Dolly Parton",
    "Luke Combs",

    # Latin
    "Shakira",
    "Bad Bunny",

    # Funk / disco / soul
    "CHIC",
    "Earth, Wind & Fire",

    # Reggae
    "Bob Marley & The Wailers",

    # Metal
    "Metallica",

    # Jazz
    "Miles Davis"
]


url = "https://musicbrainz.org/ws/2/recording/"

headers = {
    "User-Agent": "SetFlow/1.0"
}


# Pagination settings
page_size = 25
max_pages = 3


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

    print(f"\n=== Extracting: {artist} ===")

    for page_number in range(max_pages):

        offset = page_number * page_size

        print(
            f"\nPage {page_number + 1} "
            f"(offset {offset})"
        )

        params = {
            "query": f'artist:"{artist}"',
            "fmt": "json",
            "limit": page_size,
            "offset": offset
        }

        response = request_musicbrainz(params)

        if response is None:
            print(
                f"Skipping page {page_number + 1} "
                f"for {artist}."
            )
            continue

        data = response.json()

        recordings = data.get("recordings", [])

        print(
            "Total matches reported by MusicBrainz:",
            data.get("count", 0)
        )

        print(
            "Recordings downloaded on this page:",
            len(recordings)
        )

        safe_artist_name = (
            artist.lower()
            .replace(" ", "_")
            .replace(".", "")
            .replace(",", "")
            .replace("&", "and")
        )

        raw_file = raw_folder / (
            f"{safe_artist_name}_"
            f"page_{page_number + 1}_"
            f"{timestamp}.json"
        )

        raw_file.write_text(
            response.text,
            encoding="utf-8"
        )

        print(
            "Raw response saved to:",
            raw_file
        )

        if len(recordings) < page_size:
            print("Reached the final page.")
            break

        # MusicBrainz asks clients not to make requests too quickly.
        time.sleep(1)


print("\nCatalogue pagination extraction finished.")