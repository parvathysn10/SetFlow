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
# AVAILABLE MUSIC POOLS
# --------------------------------------------------

AVAILABLE_POOLS = [
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
    "jazz"
]


# --------------------------------------------------
# COMMAND-LINE INPUT
# --------------------------------------------------

if len(sys.argv) >= 2:
    occasion = sys.argv[1].lower()
else:
    occasion = "party"


if len(sys.argv) >= 3:
    try:
        requested_minutes = int(sys.argv[2])
    except ValueError:
        print("Duration must be a whole number of minutes.")
        sys.exit(1)
else:
    requested_minutes = 30


if requested_minutes <= 0:
    print("Duration must be greater than zero.")
    sys.exit(1)


if occasion not in PROFILES:
    print("Unknown occasion:", occasion)
    print(
        "Choose from:",
        ", ".join(PROFILES.keys())
    )
    sys.exit(1)


# Any arguments after occasion and duration are
# interpreted as requested music pools.
if len(sys.argv) >= 4:
    requested_pools = [
        pool.lower()
        for pool in sys.argv[3:]
    ]
else:
    requested_pools = ["all"]


if "all" in requested_pools:
    requested_pools = ["all"]
else:
    invalid_pools = [
        pool
        for pool in requested_pools
        if pool not in AVAILABLE_POOLS
    ]

    if invalid_pools:
        print(
            "Unknown music pool(s):",
            ", ".join(invalid_pools)
        )

        print(
            "\nChoose from:"
        )

        for pool in AVAILABLE_POOLS:
            print(" -", pool)

        print(" - all")

        sys.exit(1)


profile = PROFILES[occasion]


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

connection = duckdb.connect(
    str(DATABASE_FILE)
)


# --------------------------------------------------
# GET CANDIDATES USING SQL
# --------------------------------------------------

base_query = """
    SELECT DISTINCT
        t.recording_mbid,
        t.title,
        t.artist,
        t.length_seconds,
        t.bpm,
        t.musical_key,
        t.scale,
        t.danceability,
        t.average_loudness,
        t.dynamic_complexity,
        t.onset_rate,

        (
            ABS(t.bpm - ?)
            +
            ABS(t.danceability - ?) * 20
        ) AS occasion_distance

    FROM tracks AS t
"""


parameters = [
    profile["target_bpm"],
    profile["target_danceability"]
]


# Only join/filter by music pool when the user
# has requested particular pools.
if requested_pools != ["all"]:

    placeholders = ", ".join(
        ["?"] * len(requested_pools)
    )

    base_query += """
        INNER JOIN track_music_pools AS p
            ON t.recording_mbid = p.recording_mbid
    """

    pool_filter = (
        f"AND p.music_pool IN ({placeholders})"
    )

else:
    pool_filter = ""


base_query += f"""
    WHERE
        t.bpm BETWEEN ? AND ?
        AND t.length_seconds IS NOT NULL
        AND t.bpm IS NOT NULL
        AND t.musical_key IS NOT NULL
        AND t.scale IS NOT NULL
        AND t.danceability IS NOT NULL

        {pool_filter}

    ORDER BY occasion_distance ASC
"""


parameters.extend([
    profile["target_bpm"]
    - profile["bpm_range"],

    profile["target_bpm"]
    + profile["bpm_range"]
])


if requested_pools != ["all"]:
    parameters.extend(
        requested_pools
    )


candidates = connection.execute(
    base_query,
    parameters
).fetchall()


# --------------------------------------------------
# CHECK WHETHER FILTERING FOUND ANYTHING
# --------------------------------------------------

if not candidates:

    print(
        "\nNo tracks matched that combination."
    )

    print(
        "Try another music pool, occasion, "
        "or use 'all'."
    )

    connection.close()
    sys.exit(0)


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

    # Lower score = smoother according to
    # SetFlow's transparent heuristic.
    return (
        bpm_change
        + harmonic_change * 2
        + danceability_change * 5
    )


# --------------------------------------------------
# ORDER TRACKS USING GREEDY TRANSITION ALGORITHM
# --------------------------------------------------

if selected_tracks:

    remaining_tracks = (
        selected_tracks.copy()
    )

    first_track = min(
        remaining_tracks,
        key=lambda track: track[4]
    )

    ordered_tracks = [
        first_track
    ]

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


if requested_pools == ["all"]:
    pool_display = "All available music pools"
else:
    pool_display = ", ".join(
        pool.replace("_", " ").title()
        for pool in requested_pools
    )


output_lines.append(
    f"Music pools: {pool_display}"
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


if requested_pools == ["all"]:

    pool_filename = "all"

else:

    pool_filename = "-".join(
        requested_pools
    )


OUTPUT_FILE = (
    OUTPUT_FOLDER
    / (
        f"{occasion}_"
        f"{requested_minutes}min_"
        f"{pool_filename}_set.txt"
    )
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
