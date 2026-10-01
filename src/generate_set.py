import sys
from pathlib import Path

import duckdb


DATABASE_FILE = Path(
    "data/setflow.duckdb"
)


# --------------------------------
# Occasion profiles
# --------------------------------
#
# These are transparent rules.
# They are not claims that these
# characteristics objectively define
# a particular mood.
#

PROFILES = {

    "party": {
        "target_bpm": 125,
        "bpm_range": 35,
        "target_danceability": 1.0
    },

    "chill": {
        "target_bpm": 90,
        "bpm_range": 30,
        "target_danceability": 0.5
    },

    "warmup": {
        "target_bpm": 105,
        "bpm_range": 30,
        "target_danceability": 0.7
    }
}


# --------------------------------
# Read user input
# --------------------------------

if len(sys.argv) >= 2:
    occasion = sys.argv[1].lower()
else:
    occasion = "party"


if len(sys.argv) >= 3:
    requested_minutes = int(
        sys.argv[2]
    )
else:
    requested_minutes = 30


if occasion not in PROFILES:

    print(
        "Unknown occasion:",
        occasion
    )

    print(
        "Choose from:",
        ", ".join(PROFILES.keys())
    )

    sys.exit(1)


profile = PROFILES[occasion]


print(
    "\nSETFLOW"
)

print(
    "Occasion:",
    occasion
)

print(
    "Requested duration:",
    requested_minutes,
    "minutes"
)


# --------------------------------
# Connect to DuckDB
# --------------------------------

connection = duckdb.connect(
    str(DATABASE_FILE)
)


# --------------------------------
# Score candidate tracks
# --------------------------------
#
# We use SQL to calculate how close
# each track is to the requested
# occasion profile.
#
# Smaller differences produce
# higher scores.
#

candidates = connection.execute(
    """
    SELECT
        recording_mbid,
        title,
        artist,
        length_seconds,
        bpm,
        musical_key,
        scale,
        danceability,
        average_loudness,
        dynamic_complexity,
        onset_rate,

        ABS(bpm - ?) AS bpm_difference,

        ABS(
            danceability - ?
        ) AS danceability_difference

    FROM tracks

    WHERE bpm BETWEEN ? AND ?

    AND length_seconds IS NOT NULL

    ORDER BY
        (
            ABS(bpm - ?)
            +
            ABS(
                danceability - ?
            ) * 20
        ) ASC
    """,

    [
        profile["target_bpm"],
        profile[
            "target_danceability"
        ],

        profile["target_bpm"]
        - profile["bpm_range"],

        profile["target_bpm"]
        + profile["bpm_range"],

        profile["target_bpm"],

        profile[
            "target_danceability"
        ]
    ]

).fetchall()


print(
    "Candidate tracks:",
    len(candidates)
)


# --------------------------------
# Select enough tracks to reach
# approximately the requested time
# --------------------------------

target_seconds = (
    requested_minutes * 60
)

selected_tracks = []

total_seconds = 0


for track in candidates:

    if total_seconds >= target_seconds:
        break

    selected_tracks.append(
        track
    )

    total_seconds += (
        track[3]
    )


# --------------------------------
# Order the selected tracks
# --------------------------------
#
# For V1 we create a gradual BPM
# progression through the set.
#

selected_tracks.sort(
    key=lambda track: track[4]
)


# --------------------------------
# Key compatibility helper
# --------------------------------

def key_compatibility(
    first_key,
    first_scale,
    second_key,
    second_scale
):

    if (
        first_key == second_key
        and first_scale == second_scale
    ):
        return (
            "same key and scale"
        )

    if first_key == second_key:
        return (
            "same key, different scale"
        )

    if first_scale == second_scale:
        return (
            "same scale"
        )

    return (
        "different key and scale"
    )


# --------------------------------
# Print generated set
# --------------------------------

print(
    "\n"
    + "=" * 60
)

print(
    f"SETFLOW — "
    f"{occasion.upper()} SET"
)

print(
    "=" * 60
)


for index, track in enumerate(
    selected_tracks
):

    title = track[1]
    artist = track[2]
    bpm = track[4]
    musical_key = track[5]
    scale = track[6]
    danceability = track[7]


    print(
        f"\n{index + 1:02}. "
        f"{artist} - {title}"
    )

    print(
        f"    {bpm:.1f} BPM | "
        f"{musical_key} {scale} | "
        f"danceability "
        f"{danceability:.3f}"
    )


    # If there is another track,
    # explain the transition.
    if index < (
        len(selected_tracks) - 1
    ):

        next_track = (
            selected_tracks[
                index + 1
            ]
        )

        bpm_change = (
            next_track[4]
            - bpm
        )

        compatibility = (
            key_compatibility(
                musical_key,
                scale,
                next_track[5],
                next_track[6]
            )
        )


        print(
            "        ↓"
        )

        print(
            f"    Transition: "
            f"{bpm_change:+.1f} BPM | "
            f"{compatibility}"
        )


# --------------------------------
# Summary
# --------------------------------

actual_minutes = (
    total_seconds / 60
)


print(
    "\n"
    + "=" * 60
)

print(
    "Tracks selected:",
    len(selected_tracks)
)

print(
    f"Approximate duration: "
    f"{actual_minutes:.1f} minutes"
)

print(
    "=" * 60
)


connection.close()