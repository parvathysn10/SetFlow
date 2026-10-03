import json
import sys
from pathlib import Path


INPUT_FILE = Path(
    "data/processed/setflow_tracks.json"
)


VALID_MUSIC_POOLS = {
    "pop",
    "rnb",
    "hip_hop_rap",
    "dance_electronic",
    "indie_alternative",
    "rock",
    "country",
    "latin",
    "funk_disco",
    "reggae",
    "metal",
    "jazz",
}


# -----------------------------
# Load final processed dataset
# -----------------------------

if not INPUT_FILE.exists():

    print(
        f"FAIL: {INPUT_FILE} does not exist."
    )

    print(
        "Run join_music_data.py first."
    )

    sys.exit(1)


with INPUT_FILE.open(
    "r",
    encoding="utf-8"
) as file:

    tracks = json.load(file)


print(
    f"Validating {len(tracks)} SetFlow tracks...\n"
)


# -----------------------------
# Store validation results
# -----------------------------

checks = []


def add_check(
    name,
    passed,
    detail
):

    checks.append(
        (
            name,
            passed,
            detail
        )
    )


# -----------------------------
# Dataset-level checks
# -----------------------------

add_check(
    "Dataset is not empty",
    len(tracks) > 0,
    f"{len(tracks)} tracks found"
)


mbids = [
    track.get("recording_mbid")
    for track in tracks
]


missing_mbids = sum(
    1
    for mbid in mbids
    if not mbid
)


add_check(
    "No missing MBIDs",
    missing_mbids == 0,
    f"{missing_mbids} missing"
)


duplicate_mbids = (
    len(mbids)
    - len(set(mbids))
)


add_check(
    "MBIDs are unique",
    duplicate_mbids == 0,
    f"{duplicate_mbids} duplicates"
)


# -----------------------------
# Required recommendation fields
# -----------------------------

required_fields = [
    "title",
    "artist",
    "length_seconds",
    "bpm",
    "key",
    "scale",
    "danceability",
]


for field in required_fields:

    missing = sum(
        1
        for track in tracks
        if track.get(field) is None
    )

    add_check(
        f"No missing {field}",
        missing == 0,
        f"{missing} missing"
    )


# -----------------------------
# Track length validation
# -----------------------------

invalid_lengths = sum(
    1
    for track in tracks
    if (
        track.get("length_seconds")
        is not None
        and (
            not isinstance(
                track["length_seconds"],
                (int, float)
            )
            or track["length_seconds"] <= 0
        )
    )
)


add_check(
    "Track lengths are positive",
    invalid_lengths == 0,
    f"{invalid_lengths} invalid"
)


# -----------------------------
# BPM validation
# -----------------------------

invalid_bpms = sum(
    1
    for track in tracks
    if (
        track.get("bpm")
        is not None
        and (
            not isinstance(
                track["bpm"],
                (int, float)
            )
            or not (
                30
                <= track["bpm"]
                <= 250
            )
        )
    )
)


add_check(
    "BPM values are plausible",
    invalid_bpms == 0,
    (
        f"{invalid_bpms} "
        "outside 30-250 BPM"
    )
)


# -----------------------------
# Danceability validation
# -----------------------------

# AcousticBrainz danceability values in this
# dataset are not normalised to a 0-1 range.
# Validate that values are numeric and
# non-negative without altering source data.

invalid_danceability = sum(
    1
    for track in tracks
    if (
        track.get("danceability")
        is not None
        and (
            not isinstance(
                track["danceability"],
                (int, float)
            )
            or track["danceability"] < 0
        )
    )
)


add_check(
    "Danceability values are valid",
    invalid_danceability == 0,
    f"{invalid_danceability} invalid"
)


# -----------------------------
# Musical key and scale checks
# -----------------------------

valid_scales = {
    "major",
    "minor",
}


invalid_scales = sum(
    1
    for track in tracks
    if (
        track.get("scale")
        is not None
        and str(
            track["scale"]
        ).lower()
        not in valid_scales
    )
)


add_check(
    "Musical scales are recognised",
    invalid_scales == 0,
    f"{invalid_scales} invalid"
)


# -----------------------------
# Music-pool checks
# -----------------------------

tracks_without_pool = sum(
    1
    for track in tracks
    if not track.get(
        "music_pools"
    )
)


add_check(
    "Every track has a music pool",
    tracks_without_pool == 0,
    (
        f"{tracks_without_pool} "
        "without a pool"
    )
)


unknown_pools = set()


for track in tracks:

    for pool in track.get(
        "music_pools",
        []
    ):

        if pool not in VALID_MUSIC_POOLS:

            unknown_pools.add(
                pool
            )


add_check(
    "All music pools are recognised",
    len(unknown_pools) == 0,
    (
        "none"
        if not unknown_pools
        else ", ".join(
            sorted(
                unknown_pools
            )
        )
    )
)


# -----------------------------
# Duplicate pool assignments
# -----------------------------

duplicate_pool_assignments = 0


for track in tracks:

    pools = track.get(
        "music_pools",
        []
    )

    duplicate_pool_assignments += (
        len(pools)
        - len(set(pools))
    )


add_check(
    "No duplicate music-pool assignments",
    duplicate_pool_assignments == 0,
    (
        f"{duplicate_pool_assignments} "
        "duplicates"
    )
)


# -----------------------------
# Print validation report
# -----------------------------

print(
    "--- SetFlow data quality checks ---\n"
)


for name, passed, detail in checks:

    status = (
        "PASS"
        if passed
        else "FAIL"
    )

    print(
        f"{status}: "
        f"{name} "
        f"({detail})"
    )


# -----------------------------
# Final result
# -----------------------------

failed_checks = [
    check
    for check in checks
    if not check[1]
]


print()


if failed_checks:

    print(
        "VALIDATION FAILED: "
        f"{len(failed_checks)} "
        "check(s) failed."
    )

    sys.exit(1)


print(
    "VALIDATION PASSED: "
    f"all {len(checks)} "
    "checks passed."
)