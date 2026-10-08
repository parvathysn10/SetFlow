
import json
from pathlib import Path
from collections import Counter

PROCESSED = Path("data/processed")
RAW = Path("data/raw/catalogue")


def load_json(filename):
    with (PROCESSED / filename).open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)


def main():
    catalogue = load_json(
        "musicbrainz_catalogue_clean.json"
    )
    acoustic = load_json(
        "acousticbrainz_features_clean.json"
    )
    tracks = load_json("setflow_tracks.json")

    raw_files = sorted(RAW.glob("*.json"))
    raw_record_count = 0

    for path in raw_files:
        with path.open("r", encoding="utf-8") as file:
            raw_record_count += len(
                json.load(file).get("recordings", [])
            )

    alternative_count = sum(
        bool(record.get("is_alternative_version"))
        for record in catalogue
    )

    eligible_count = len(catalogue) - alternative_count
    unmatched_count = eligible_count - len(tracks)

    pool_counts = Counter(
        pool
        for track in tracks
        for pool in track.get("music_pools", [])
    )

    print("\n" + "=" * 48)
    print("SETFLOW DATA QUALITY REPORT")
    print("=" * 48)

    print("\nSOURCE AND TRANSFORMATION")
    print(f"Raw MusicBrainz files:         {len(raw_files)}")
    print(f"Raw recording occurrences:     {raw_record_count}")
    print(f"Clean unique recordings:       {len(catalogue)}")
    print(f"Alternative versions flagged:  {alternative_count}")
    print(f"Eligible recordings:           {eligible_count}")
    print(f"Acoustic feature records:      {len(acoustic)}")
    print(f"Final joined tracks:           {len(tracks)}")

    print("\nCOVERAGE")
    print(f"Eligible without acoustic match: {unmatched_count}")

    if eligible_count:
        coverage = 100 * len(tracks) / eligible_count
        print(f"Final join coverage:             {coverage:.1f}%")

    print("\nFINAL DATA QUALITY")
    mbids = [track.get("recording_mbid") for track in tracks]
    print(f"Duplicate MBIDs:              {len(mbids) - len(set(mbids))}")

    for field in [
        "title", "artist", "length_seconds",
        "bpm", "key", "scale", "danceability"
    ]:
        missing = sum(
            track.get(field) is None
            for track in tracks
        )
        print(f"Missing {field}: {missing}")

    print("\nFINAL TRACKS BY MUSIC POOL")
    for pool, count in sorted(pool_counts.items()):
        print(f"{pool}: {count}")

    print("\nNote: Music pools can overlap.")
    print("Raw recording occurrences can include repeated MBIDs.")
    print("Run validate_data.py for the full 17 checks.")
    print("=" * 48)


if __name__ == "__main__":
    main()
