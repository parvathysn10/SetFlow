import json
from pathlib import Path


raw_folder = Path("data/raw/catalogue")
processed_folder = Path("data/processed")

processed_folder.mkdir(parents=True, exist_ok=True)

raw_files = list(raw_folder.glob("*.json"))

if not raw_files:
    print("No raw catalogue files found.")
    exit()


clean_recordings = []
seen_mbids = set()

duplicate_count = 0
missing_mbid_count = 0
missing_length_count = 0


alternative_keywords = [
    "live",
    "dolby atmos",
    "remix",
    "instrumental",
    "karaoke",
    "acoustic",
    "demo"
]


for raw_file in raw_files:

    print("Reading:", raw_file)

    with raw_file.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    for recording in raw_data.get("recordings", []):

        recording_mbid = recording.get("id")

        # A recording without an MBID cannot be reliably joined later.
        if not recording_mbid:
            missing_mbid_count += 1
            continue

        # MBID is our unique recording identifier.
        # Skip it if we have already processed the same recording.
        if recording_mbid in seen_mbids:
            duplicate_count += 1
            continue

        seen_mbids.add(recording_mbid)

        artist_names = []

        for artist_credit in recording.get("artist-credit", []):
            artist = artist_credit.get("artist", {})
            artist_name = artist.get("name")

            if artist_name:
                artist_names.append(artist_name)

        if artist_names:
            artist_text = ", ".join(artist_names)
        else:
            artist_text = "Unknown"

        length_ms = recording.get("length")

        if length_ms is not None:
            length_seconds = round(length_ms / 1000, 1)
        else:
            length_seconds = None
            missing_length_count += 1

        disambiguation = recording.get("disambiguation") or ""
        disambiguation_lower = disambiguation.lower()

        is_alternative_version = any(
            keyword in disambiguation_lower
            for keyword in alternative_keywords
        )

        is_video = recording.get("video")

        if is_video is None:
            is_video = False

        clean_recording = {
            "recording_mbid": recording_mbid,
            "title": recording.get("title") or "Unknown",
            "artist": artist_text,
            "length_seconds": length_seconds,
            "disambiguation": disambiguation,
            "is_alternative_version": is_alternative_version,
            "is_video": is_video
        }

        clean_recordings.append(clean_recording)


processed_file = (
    processed_folder / "musicbrainz_catalogue_clean.json"
)

with processed_file.open("w", encoding="utf-8") as file:
    json.dump(
        clean_recordings,
        file,
        indent=4,
        ensure_ascii=False
    )


print("\n--- Catalogue quality summary ---")
print("Raw files processed:", len(raw_files))
print("Clean unique recordings:", len(clean_recordings))
print("Duplicate MBIDs removed:", duplicate_count)
print("Records missing MBID:", missing_mbid_count)
print("Records missing length:", missing_length_count)

alternative_count = sum(
    recording["is_alternative_version"]
    for recording in clean_recordings
)

print("Alternative versions flagged:", alternative_count)

print("\nClean catalogue saved to:", processed_file)