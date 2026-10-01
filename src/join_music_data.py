import json
from pathlib import Path


MUSICBRAINZ_FILE = Path(
    "data/processed/musicbrainz_catalogue_clean.json"
)

ACOUSTICBRAINZ_FILE = Path(
    "data/processed/acousticbrainz_features_clean.json"
)

OUTPUT_FILE = Path(
    "data/processed/setflow_tracks.json"
)


# -----------------------------
# Load the two clean datasets
# -----------------------------

with MUSICBRAINZ_FILE.open(
    "r",
    encoding="utf-8"
) as file:
    musicbrainz_records = json.load(file)


with ACOUSTICBRAINZ_FILE.open(
    "r",
    encoding="utf-8"
) as file:
    acoustic_records = json.load(file)


print(
    "MusicBrainz records:",
    len(musicbrainz_records)
)

print(
    "AcousticBrainz records:",
    len(acoustic_records)
)


# --------------------------------------------------
# Create a lookup using the MusicBrainz recording ID
# --------------------------------------------------

acoustic_lookup = {
    record["recording_mbid"]: record
    for record in acoustic_records
}


# -----------------------------
# Join the datasets
# -----------------------------

joined_records = []

no_acoustic_match = 0
alternative_versions_excluded = 0


for recording in musicbrainz_records:

    # Alternative versions are not part of the
    # main SetFlow recommendation catalogue.
    if recording.get(
        "is_alternative_version",
        False
    ):
        alternative_versions_excluded += 1
        continue


    mbid = recording["recording_mbid"]

    acoustic = acoustic_lookup.get(mbid)


    if acoustic is None:
        no_acoustic_match += 1
        continue


    joined_record = {
        "recording_mbid": mbid,

        "title": recording.get(
            "title"
        ),

        "artist": recording.get(
            "artist"
        ),

        "length_seconds": recording.get(
            "length_seconds"
        ),

        "bpm": acoustic.get(
            "bpm"
        ),

        "key": acoustic.get(
            "key"
        ),

        "scale": acoustic.get(
            "scale"
        ),

        "danceability": acoustic.get(
            "danceability"
        ),

        "average_loudness": acoustic.get(
            "average_loudness"
        ),

        "dynamic_complexity": acoustic.get(
            "dynamic_complexity"
        ),

        "onset_rate": acoustic.get(
            "onset_rate"
        ),

        "acoustic_length_seconds": acoustic.get(
            "acoustic_length_seconds"
        )
    }


    joined_records.append(
        joined_record
    )


# -----------------------------
# Basic validation
# -----------------------------

joined_mbids = [
    record["recording_mbid"]
    for record in joined_records
]

duplicate_joined_mbids = (
    len(joined_mbids)
    - len(set(joined_mbids))
)


missing_bpm = sum(
    1
    for record in joined_records
    if record["bpm"] is None
)

missing_key = sum(
    1
    for record in joined_records
    if record["key"] is None
)

missing_length = sum(
    1
    for record in joined_records
    if record["length_seconds"] is None
)


# -----------------------------------------
# Compare lengths from the two data sources
# -----------------------------------------

length_mismatches = 0

for record in joined_records:

    musicbrainz_length = record[
        "length_seconds"
    ]

    acoustic_length = record[
        "acoustic_length_seconds"
    ]

    if (
        musicbrainz_length is not None
        and acoustic_length is not None
    ):

        difference = abs(
            musicbrainz_length
            - acoustic_length
        )

        # Flag if the two sources disagree
        # by more than 5 seconds.
        if difference > 5:
            length_mismatches += 1


# -----------------------------
# Save joined dataset
# -----------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


with OUTPUT_FILE.open(
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        joined_records,
        file,
        indent=4,
        ensure_ascii=False
    )


# -----------------------------
# Quality summary
# -----------------------------

print(
    "\n--- SetFlow join summary ---"
)

print(
    "MusicBrainz catalogue records:",
    len(musicbrainz_records)
)

print(
    "AcousticBrainz records:",
    len(acoustic_records)
)

print(
    "Alternative versions excluded:",
    alternative_versions_excluded
)

print(
    "Eligible records without acoustic match:",
    no_acoustic_match
)

print(
    "Joined SetFlow tracks:",
    len(joined_records)
)

print(
    "Duplicate MBIDs after join:",
    duplicate_joined_mbids
)

print(
    "Missing BPM after join:",
    missing_bpm
)

print(
    "Missing key after join:",
    missing_key
)

print(
    "Missing MusicBrainz length:",
    missing_length
)

print(
    "Length disagreements over 5 seconds:",
    length_mismatches
)

print(
    "\nJoined SetFlow dataset saved to:",
    OUTPUT_FILE
)