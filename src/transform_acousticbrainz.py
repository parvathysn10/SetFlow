import json
from pathlib import Path


RAW_FOLDER = Path("data/raw/acousticbrainz")

OUTPUT_FILE = Path(
    "data/processed/acousticbrainz_features_clean.json"
)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


clean_records = []

missing_bpm = 0
missing_key = 0
missing_danceability = 0


raw_files = list(
    RAW_FOLDER.glob("*_lowlevel.json")
)


print(
    f"AcousticBrainz files found: {len(raw_files)}\n"
)


for raw_file in raw_files:

    print("Reading:", raw_file)

    with raw_file.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)


    # The MBID is already contained in our filename.
    mbid = raw_file.name.replace(
        "_lowlevel.json",
        ""
    )


    rhythm = data.get(
        "rhythm",
        {}
    )

    tonal = data.get(
        "tonal",
        {}
    )

    lowlevel = data.get(
        "lowlevel",
        {}
    )

    metadata = data.get(
        "metadata",
        {}
    )

    audio_properties = metadata.get(
        "audio_properties",
        {}
    )


    bpm = rhythm.get("bpm")

    danceability = rhythm.get(
        "danceability"
    )

    key = tonal.get(
        "key_key"
    )

    scale = tonal.get(
        "key_scale"
    )

    average_loudness = lowlevel.get(
        "average_loudness"
    )

    dynamic_complexity = lowlevel.get(
        "dynamic_complexity"
    )

    onset_rate = rhythm.get(
        "onset_rate"
    )

    acoustic_length = audio_properties.get(
        "length"
    )


    if bpm is None:
        missing_bpm += 1

    if key is None:
        missing_key += 1

    if danceability is None:
        missing_danceability += 1


    clean_record = {
        "recording_mbid": mbid,
        "bpm": bpm,
        "key": key,
        "scale": scale,
        "danceability": danceability,
        "average_loudness": average_loudness,
        "dynamic_complexity": dynamic_complexity,
        "onset_rate": onset_rate,
        "acoustic_length_seconds": acoustic_length
    }


    clean_records.append(
        clean_record
    )


with OUTPUT_FILE.open(
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        clean_records,
        file,
        indent=4,
        ensure_ascii=False
    )


print(
    "\n--- AcousticBrainz transformation summary ---"
)

print(
    "Raw files processed:",
    len(raw_files)
)

print(
    "Clean acoustic records:",
    len(clean_records)
)

print(
    "Missing BPM:",
    missing_bpm
)

print(
    "Missing key:",
    missing_key
)

print(
    "Missing danceability:",
    missing_danceability
)

print(
    "\nClean acoustic data saved to:",
    OUTPUT_FILE
)