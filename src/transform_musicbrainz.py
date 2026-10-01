import json
from pathlib import Path


raw_folder = Path("data/raw")
processed_folder = Path("data/processed")

processed_folder.mkdir(parents=True, exist_ok=True)


raw_files = list(
    raw_folder.glob("musicbrainz_successful_search_*.json")
)

if not raw_files:
    print("No raw MusicBrainz files found.")
    exit()


latest_file = max(
    raw_files,
    key=lambda file: file.stat().st_mtime
)

print("Reading raw file:", latest_file)


with latest_file.open("r", encoding="utf-8") as file:
    raw_data = json.load(file)


clean_recordings = []


for recording in raw_data["recordings"]:

    artist_names = []

    for artist_credit in recording.get("artist-credit", []):
        artist = artist_credit.get("artist", {})

        artist_names.append(
            artist.get("name", "Unknown")
        )

    length_ms = recording.get("length")

    if length_ms is not None:
        length_seconds = round(length_ms / 1000, 1)
    else:
        length_seconds = None

    disambiguation = recording.get("disambiguation") or ""

    disambiguation_lower = disambiguation.lower()

    is_alternative_version = (
        "live" in disambiguation_lower
        or "dolby atmos" in disambiguation_lower
    )

    is_video = recording.get("video")

    if is_video is None:
        is_video = False

    clean_recording = {
        "recording_mbid": recording.get("id"),
        "title": recording.get("title"),
        "artist": ", ".join(artist_names),
        "length_seconds": length_seconds,
        "disambiguation": disambiguation,
        "is_alternative_version": is_alternative_version,
        "is_video": is_video
    }

    clean_recordings.append(clean_recording)


processed_file = Path(
    "data/processed/musicbrainz_recordings_clean.json"
)

with processed_file.open(
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        clean_recordings,
        file,
        indent=4,
        ensure_ascii=False
    )


print("\nClean recordings:")

for recording in clean_recordings:
    print(recording)

print(
    "\nClean data saved to:",
    processed_file
)