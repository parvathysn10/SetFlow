import time
from datetime import datetime
from pathlib import Path

import requests


url = "https://musicbrainz.org/ws/2/recording/"

params = {
    "query": 'recording:"successful" AND artist:"Ariana Grande"',
    "fmt": "json"
}

headers = {
    "User-Agent": "SetFlow/1.0"
}

max_attempts = 3

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
            break

    except requests.RequestException as error:
        print(f"Attempt {attempt} failed: {error}")

    if attempt < max_attempts:
        print("Waiting before trying again...")
        time.sleep(2)

else:
    print("MusicBrainz request failed after 3 attempts.")
    exit()


data = response.json()

print("Number of results:", data["count"])

for recording in data["recordings"]:
    print(
        recording["title"],
        "-",
        recording.get("disambiguation", "")
    )


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

raw_file = Path(
    f"data/raw/musicbrainz_successful_search_{timestamp}.json"
)

raw_file.write_text(
    response.text,
    encoding="utf-8"
)

print("Raw response saved to:", raw_file)