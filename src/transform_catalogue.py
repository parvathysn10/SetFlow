import json
from pathlib import Path


raw_folder = Path("data/raw/catalogue")
processed_folder = Path("data/processed")

processed_folder.mkdir(parents=True, exist_ok=True)

raw_files = list(raw_folder.glob("*.json"))

if not raw_files:
    print("No raw catalogue files found.")
    exit()


# These are prototype music pools, not authoritative track-level genres.
# They describe why each seed artist was included in the development
# catalogue. Individual recordings may span multiple genres/styles.
artist_music_pools = {
    "Ariana Grande": ["pop"],
    "Dua Lipa": ["pop", "dance_electronic"],
    "Lady Gaga": ["pop", "dance_electronic"],

    "SZA": ["rnb"],
    "The Weeknd": ["rnb", "pop"],

    "Travis Scott": ["hip_hop_rap"],
    "Don Toliver": ["hip_hop_rap", "rnb"],

    "Calvin Harris": ["dance_electronic"],
    "Daft Punk": ["dance_electronic", "funk_disco"],
    "Disclosure": ["dance_electronic"],

    "Arctic Monkeys": ["indie_alternative", "rock"],
    "Tame Impala": ["indie_alternative"],

    "Foo Fighters": ["rock"],
    "Fleetwood Mac": ["rock"],

    "Dolly Parton": ["country"],
    "Luke Combs": ["country"],

    "Shakira": ["latin", "pop"],
    "Bad Bunny": ["latin"],

    "Chic": ["funk_disco"],
    "Earth, Wind & Fire": ["funk_disco"],

    "Bob Marley & The Wailers": ["reggae"],

    "Metallica": ["metal", "rock"],

    "Miles Davis": ["jazz"]
}


clean_recordings_by_mbid = {}

duplicate_count = 0
missing_mbid_count = 0
missing_length_count = 0
unintended_artist_count = 0


# Words commonly indicating that a recording is an alternative
# version rather than the main/original recording.
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

        artist_names = []

        for artist_credit in recording.get("artist-credit", []):
            artist = artist_credit.get("artist", {})
            artist_name = artist.get("name")

            if artist_name:
                artist_names.append(artist_name)

        # Keep a recording only when at least one credited artist is one
        # of SetFlow's intended seed artists. This removes search
        # false-positives while retaining legitimate collaborations.
        matched_seed_artists = [
            artist_name
            for artist_name in artist_names
            if artist_name in artist_music_pools
        ]

        if not matched_seed_artists:
            unintended_artist_count += 1
            continue

        # A recording can belong to more than one prototype music pool.
        # Example: a seed artist may contribute to both pop and dance.
        music_pools = sorted({
            pool
            for artist_name in matched_seed_artists
            for pool in artist_music_pools[artist_name]
        })

        if artist_names:
            artist_text = ", ".join(artist_names)
        else:
            artist_text = "Unknown"

        # If this MBID has already appeared in another raw response,
        # keep one recording but merge any additional seed artists/pools.
        if recording_mbid in clean_recordings_by_mbid:
            duplicate_count += 1

            existing = clean_recordings_by_mbid[recording_mbid]

            existing["seed_artists"] = sorted(
                set(
                    existing["seed_artists"]
                    + matched_seed_artists
                )
            )

            existing["music_pools"] = sorted(
                set(
                    existing["music_pools"]
                    + music_pools
                )
            )

            continue

        length_ms = recording.get("length")

        if length_ms is not None:
            length_seconds = round(
                length_ms / 1000,
                1
            )
        else:
            length_seconds = None
            missing_length_count += 1

        # Check both the recording title and MusicBrainz
        # disambiguation text for alternative-version indicators.
        #
        # Previously only disambiguation was checked, which meant
        # recordings with titles such as "(... remix)" could slip
        # into the recommendation catalogue.
        disambiguation = (
            recording.get("disambiguation")
            or ""
        )

        title = (
            recording.get("title")
            or "Unknown"
        )

        version_text = (
            f"{title} {disambiguation}"
        ).lower()

        is_alternative_version = any(
            keyword in version_text
            for keyword in alternative_keywords
        )

        is_video = recording.get("video")

        if is_video is None:
            is_video = False

        clean_recording = {
            "recording_mbid": recording_mbid,
            "title": title,
            "artist": artist_text,
            "seed_artists": sorted(
                matched_seed_artists
            ),
            "music_pools": music_pools,
            "length_seconds": length_seconds,
            "disambiguation": disambiguation,
            "is_alternative_version": (
                is_alternative_version
            ),
            "is_video": is_video
        }

        clean_recordings_by_mbid[
            recording_mbid
        ] = clean_recording


clean_recordings = list(
    clean_recordings_by_mbid.values()
)


processed_file = (
    processed_folder
    / "musicbrainz_catalogue_clean.json"
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


# -----------------------------
# Quality summary
# -----------------------------

print(
    "\n--- Catalogue quality summary ---"
)

print(
    "Raw files processed:",
    len(raw_files)
)

print(
    "Clean unique recordings:",
    len(clean_recordings)
)

print(
    "Duplicate MBIDs removed/merged:",
    duplicate_count
)

print(
    "Records missing MBID:",
    missing_mbid_count
)

print(
    "Unintended artist search matches excluded:",
    unintended_artist_count
)

print(
    "Records missing length:",
    missing_length_count
)


alternative_count = sum(
    recording["is_alternative_version"]
    for recording in clean_recordings
)


print(
    "Alternative versions flagged:",
    alternative_count
)


# -----------------------------
# Music pool coverage
# -----------------------------

pool_counts = {}


for recording in clean_recordings:

    for pool in recording["music_pools"]:

        pool_counts[pool] = (
            pool_counts.get(pool, 0)
            + 1
        )


print(
    "\n--- Prototype music pool coverage ---"
)


for pool, count in sorted(
    pool_counts.items()
):

    print(
        f"{pool}: {count}"
    )


print(
    "\nClean catalogue saved to:",
    processed_file
)