import requests
from pathlib import Path
from datetime import datetime

url = "https://musicbrainz.org/ws/2/recording/"

params = {
    "query": 'recording:"successful" AND artist:"Ariana Grande"',
    "fmt": "json"
}

response = requests.get(url, params=params)

print("Status code:", response.status_code)

if response.status_code != 200:
    print("MusicBrainz request failed. Raw data will not be processed.")
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

raw_file.write_text(response.text, encoding="utf-8")

print("Raw response saved to:", raw_file)