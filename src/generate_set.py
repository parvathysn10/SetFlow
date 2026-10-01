import sys
from pathlib import Path

import duckdb


DATABASE_FILE = Path("data/setflow.duckdb")


# --------------------------------------------------
# OCCASION PROFILES
# --------------------------------------------------
# These are transparent, rule-based preferences.
# They are not claims that there is one objectively
# correct musical definition of each occasion.

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


# --------------------------------------------------
# COMMAND-LINE INPUT
# --------------------------------------------------

if len(sys.argv) >= 2:
    occasion = sys.argv[1].lower()
else:
    occasion = "party"


if len(sys.argv) >= 3:
    requested_minutes = int(sys.argv[2])
else:
    requested_minutes = 30


if occasion not in PROFILES:
    print("Unknown occasion:", occasion)
    print("Choose from:", ", ".join(PROFILES.keys()))
    sys.exit(1)


profile = PROFILES[occasion]


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

connection = duckdb.connect(str(DATABASE_FILE))


# --------------------------------------------------
# GET CANDIDATES USING SQL
# --------------------------------------------------

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

        (
            ABS(bpm - ?)
            +
            ABS(danceability - ?) * 20
        ) AS occasion_distance

    FROM tracks

    WHERE
        bpm BETWEEN ? AND ?
        AND length_seconds IS NOT NULL
        AND bpm IS NOT NULL
        AND musical_key IS NOT NULL
        AND scale IS NOT NULL
        AND danceability IS NOT NULL

    ORDER BY occasion_distance ASC
    """,

    [
        profile["target_bpm"],
        profile["target_danceability"],

        profile["target_bpm"]
        - profile["bpm_range"],

        profile["target_bpm"]
        + profile["bpm_range"]
    ]
).fetchall()


# --------------------------------------------------
# SELECT ENOUGH TRACKS FOR REQUESTED DURATION
# --------------------------------------------------

target_seconds = requested_minutes * 60

selected_tracks = []
total_seconds = 0


for track in candidates:

    if total_seconds >= target_seconds:
        break

    selected_tracks.append(track)
    total_seconds += track[3]


# --------------------------------------------------
# MUSICAL KEY HELPERS
# --------------------------------------------------

# Pitch classes let us measure how far apart two
# musical keys are around the 12-note chromatic scale.

PITCH_CLASSES = {
    "C": 0,
    "C#": 1,
    "D": 2,
    "D#": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "G": 7,
    "G#": 8,
    "A": 9,
    "A#": 10,
    "B": 11
}


def circular_key_distance(key_a, key_b):

    if (
        key_a not in PITCH_CLASSES
        or key_b not in PITCH_CLASSES
    ):
        return 6

    first = PITCH_CLASSES[key_a]
    second = PITCH_CLASSES[key_b]

    difference = abs(first - second)

    return min(
        difference,
        12 - difference
    )


def harmonic_penalty(
    key_a,
    scale_a,
    key_b,
    scale_b
):

    # Exact same key and mode.
    if (
        key_a == key_b
        and scale_a == scale_b
    ):
        return 0


    # Relative major/minor relationships.
    #
    # Major -> relative minor = -3 semitones
    # Minor -> relative major = +3 semitones.

    if (
        scale_a == "major"
        and scale_b == "minor"
    ):

        expected_minor = (
            PITCH_CLASSES.get(key_a, -100)
            - 3
        ) % 12

        if (
            PITCH_CLASSES.get(key_b)
            == expected_minor
        ):
            return 0.5


    if (
        scale_a == "minor"
        and scale_b == "major"
    ):

        expected_major = (
            PITCH_CLASSES.get(key_a, -100)
            + 3
        ) % 12

        if (
            PITCH_CLASSES.get(key_b)
            == expected_major
        ):
            return 0.5


    distance = circular_key_distance(
        key_a,
        key_b
    )


    # Same tonic but major/minor changes.
    if key_a == key_b:
        return 1.0


    # Nearby pitch classes receive a
    # smaller penalty than distant ones.
    scale_penalty = (
        0 if scale_a == scale_b else 1
    )

    return (
        distance
        + scale_penalty
    )


def transition_score(
    current_track,
    next_track
):

    bpm_change = abs(
        current_track[4]
        - next_track[4]
    )

    harmonic_change = harmonic_penalty(
        current_track[5],
        current_track[6],
        next_track[5],
        next_track[6]
    )

    danceability_change = abs(
        current_track[7]
        - next_track[7]
    )

    # Lower score = smoother transition.
    #
    # BPM has the largest influence,
    # followed by harmonic compatibility,
    # then danceability continuity.

    return (
        bpm_change
        + harmonic_change * 2
        + danceability_change * 5
    )


# --------------------------------------------------
# ORDER TRACKS USING A GREEDY TRANSITION ALGORITHM
# --------------------------------------------------
#
# Instead of simply sorting everything by BPM:
#
# 1. Start with the lowest-BPM selected track.
# 2. Compare every remaining track.
# 3. Choose the track with the lowest transition score.
# 4. Repeat until every track is ordered.
#
# This is intentionally explainable rather than
# presented as an objectively optimal DJ mix.

if selected_tracks:

    remaining_tracks = selected_tracks.copy()

    first_track = min(
        remaining_tracks,
        key=lambda track: track[4]
    )

    ordered_tracks = [first_track]

    remaining_tracks.remove(
        first_track
    )


    while remaining_tracks:

        current_track = (
            ordered_tracks[-1]
        )

        next_track = min(
            remaining_tracks,
            key=lambda track:
                transition_score(
                    current_track,
                    track
                )
        )

        ordered_tracks.append(
            next_track
        )

        remaining_tracks.remove(
            next_track
        )

else:
    ordered_tracks = []


# --------------------------------------------------
# TRANSITION EXPLANATION
# --------------------------------------------------

def explain_harmonic_transition(
    first_track,
    second_track
):

    first_key = first_track[5]
    first_scale = first_track[6]

    second_key = second_track[5]
    second_scale = second_track[6]


    if (
        first_key == second_key
        and first_scale == second_scale
    ):
        return "same key and scale"


    penalty = harmonic_penalty(
        first_key,
        first_scale,
        second_key,
        second_scale
    )


    if penalty == 0.5:
        return "relative major/minor"


    if first_key == second_key:
        return "same tonic, different scale"


    if first_scale == second_scale:
        return "same scale, different key"


    return "different key and scale"


# --------------------------------------------------
# CREATE OUTPUT
# --------------------------------------------------

output_lines = []

output_lines.append(
    "=" * 64
)

output_lines.append(
    f"SETFLOW — {occasion.upper()} SET"
)

output_lines.append(
    "=" * 64
)

output_lines.append(
    f"Requested duration: "
    f"{requested_minutes} minutes"
)

output_lines.append(
    f"Candidate tracks considered: "
    f"{len(candidates)}"
)

output_lines.append("")


for index, track in enumerate(
    ordered_tracks
):

    title = track[1]
    artist = track[2]
    bpm = track[4]
    musical_key = track[5]
    scale = track[6]
    danceability = track[7]


    output_lines.append(
        f"{index + 1:02}. "
        f"{artist} - {title}"
    )

    output_lines.append(
        f"    {bpm:.1f} BPM | "
        f"{musical_key} {scale} | "
        f"danceability "
        f"{danceability:.3f}"
    )


    if index < len(
        ordered_tracks
    ) - 1:

        next_track = (
            ordered_tracks[
                index + 1
            ]
        )

        bpm_change = (
            next_track[4]
            - bpm
        )

        harmonic_description = (
            explain_harmonic_transition(
                track,
                next_track
            )
        )

        score = transition_score(
            track,
            next_track
        )


        output_lines.append(
            "        ↓"
        )

        output_lines.append(
            f"    Suggested transition: "
            f"{bpm_change:+.1f} BPM | "
            f"{harmonic_description} | "
            f"transition score "
            f"{score:.2f}"
        )


    output_lines.append("")


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

actual_minutes = (
    total_seconds / 60
)


output_lines.append(
    "=" * 64
)

output_lines.append(
    f"Tracks selected: "
    f"{len(ordered_tracks)}"
)

output_lines.append(
    f"Approximate duration: "
    f"{actual_minutes:.1f} minutes"
)

output_lines.append(
    ""
)

output_lines.append(
    "Note: SetFlow uses transparent, "
    "rule-based acoustic heuristics."
)

output_lines.append(
    "Transition suggestions are not "
    "claims of objectively optimal mixes."
)

output_lines.append(
    "=" * 64
)


# --------------------------------------------------
# PRINT OUTPUT
# --------------------------------------------------

final_output = "\n".join(
    output_lines
)

print(
    "\n" + final_output
)


# --------------------------------------------------
# SAVE OUTPUT
# --------------------------------------------------

OUTPUT_FOLDER = Path(
    "outputs"
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


OUTPUT_FILE = (
    OUTPUT_FOLDER
    / f"{occasion}_{requested_minutes}min_set.txt"
)


OUTPUT_FILE.write_text(
    final_output,
    encoding="utf-8"
)


print(
    "\nSetFlow output saved to:",
    OUTPUT_FILE
)


connection.close()