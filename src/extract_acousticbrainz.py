import json
import time
from pathlib import Path

import requests


CATALOGUE_FILE = Path(
    "data/processed/musicbrainz_catalogue_clean.json"
)

OUTPUT_FOLDER = Path(
    "data/raw/acousticbrainz"
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


with CATALOGUE_FILE.open(
    "r",
    encoding="utf-8"
) as file:
    catalogue = json.load(file)


# Keep only recordings that were not flagged
# as alternative versions.
eligible_recordings = [
    recording
    for recording in catalogue
    if not recording.get(
        "is_alternative_version",
        False
    )
]


print(
    "Clean catalogue recordings:",
    len(catalogue)
)

print(
    "Eligible for acoustic enrichment:",
    len(eligible_recordings)
)

print()


successful = 0
missing = 0
failed = 0
already_downloaded = 0


for number, recording in enumerate(
    eligible_recordings,
    start=1
):

    mbid = recording["recording_mbid"]

    output_file = (
        OUTPUT_FOLDER /
        f"{mbid}_lowlevel.json"
    )

    print(
        f"[{number}/{len(eligible_recordings)}] "
        f"{recording['artist']} - "
        f"{recording['title']}"
    )


    # Don't download a successful response again
    # if we already have it.
    if output_file.exists():

        already_downloaded += 1

        print(
            "Already downloaded - skipping."
        )

        print()

        continue


    url = (
        f"https://acousticbrainz.org/"
        f"{mbid}/low-level"
    )


    try:

        response = requests.get(
            url,
            timeout=30
        )

        print(
            "Status code:",
            response.status_code
        )


        if response.status_code == 200:

            output_file.write_text(
                response.text,
                encoding="utf-8"
            )

            successful += 1

            print(
                "Acoustic data found and saved."
            )


        elif response.status_code == 404:

            missing += 1

            print(
                "No AcousticBrainz data found."
            )


        else:

            failed += 1

            print(
                "Unexpected response:",
                response.status_code
            )


    except requests.RequestException as error:

        failed += 1

        print(
            "Request failed:",
            error
        )


    print()

    time.sleep(1)


print(
    "--- AcousticBrainz enrichment summary ---"
)

print(
    "Eligible recordings:",
    len(eligible_recordings)
)

print(
    "Already downloaded:",
    already_downloaded
)

print(
    "New acoustic files downloaded:",
    successful
)

print(
    "No AcousticBrainz data:",
    missing
)

print(
    "Failed requests:",
    failed
)

print(
    "Total acoustic files available:",
    len(
        list(
            OUTPUT_FOLDER.glob(
                "*_lowlevel.json"
            )
        )
    )
)