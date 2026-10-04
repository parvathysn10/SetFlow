from pathlib import Path
import re

import duckdb
import pandas as pd
import streamlit as st


DATABASE_FILE = Path("data/setflow.duckdb")


# --------------------------------------------------
# SETFLOW SETTINGS
# --------------------------------------------------

PROFILES = {
    "Party": {
        "target_bpm": 125,
        "bpm_range": 35,
        "target_danceability": 1.0,
    },
    "Chill": {
        "target_bpm": 90,
        "bpm_range": 30,
        "target_danceability": 0.5,
    },
    "Warm-up": {
        "target_bpm": 105,
        "bpm_range": 30,
        "target_danceability": 0.7,
    },
}


MUSIC_POOLS = {
    "Pop": "pop",
    "RnB": "rnb",
    "Hip-hop / Rap": "hip_hop_rap",
    "Dance / Electronic": "dance_electronic",
    "Indie / Alternative": "indie_alternative",
    "Rock": "rock",
    "Country": "country",
    "Latin": "latin",
    "Funk / Disco": "funk_disco",
    "Reggae": "reggae",
    "Metal": "metal",
    "Jazz": "jazz",
}


# This is intentionally a simple prototype filter.
# MusicBrainz does not provide a perfect "seasonal song"
# field, so SetFlow checks obvious seasonal terms in titles.
SEASONAL_TITLE_KEYWORDS = [
    "christmas",
    "xmas",
    "x-mas",
    "santa",
    "jingle bell",
    "jingle bells",
    "mistletoe",
    "silent night",
    "winter wonderland",
    "deck the halls",
    "o holy night",
    "little drummer boy",
    "rudolph",
    "feliz navidad",
]


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
    "B": 11,
}


# --------------------------------------------------
# CONTEXT FILTER
# --------------------------------------------------

def is_seasonal_track(title):
    title_lower = title.lower()

    return any(
        keyword in title_lower
        for keyword in SEASONAL_TITLE_KEYWORDS
    )


# --------------------------------------------------
# DUPLICATE SONG NORMALISATION
# --------------------------------------------------

def normalise_song_text(text):
    """
    Normalise artist/title text for set-level duplicate
    detection.

    This does not alter or delete the underlying source
    records stored in DuckDB.
    """

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text.lower()
    )


def song_identity(track):
    """
    Create a comparison key from normalised artist and
    title text.
    """

    artist = normalise_song_text(
        track["artist"]
    )

    title = normalise_song_text(
        track["title"]
    )

    return artist, title


# --------------------------------------------------
# TRANSITION FUNCTIONS
# --------------------------------------------------

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

    if (
        key_a == key_b
        and scale_a == scale_b
    ):
        return 0

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

    if key_a == key_b:
        return 1.0

    scale_penalty = (
        0
        if scale_a == scale_b
        else 1
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
        current_track["bpm"]
        - next_track["bpm"]
    )

    harmonic_change = harmonic_penalty(
        current_track["musical_key"],
        current_track["scale"],
        next_track["musical_key"],
        next_track["scale"],
    )

    danceability_change = abs(
        current_track["danceability"]
        - next_track["danceability"]
    )

    # Lower score = smoother according to
    # SetFlow's transparent heuristic.
    return (
        bpm_change
        + harmonic_change * 2
        + danceability_change * 5
    )


def explain_harmonic_transition(
    first_track,
    second_track
):

    first_key = first_track[
        "musical_key"
    ]

    first_scale = first_track[
        "scale"
    ]

    second_key = second_track[
        "musical_key"
    ]

    second_scale = second_track[
        "scale"
    ]

    if (
        first_key == second_key
        and first_scale == second_scale
    ):
        return "Same key and scale"

    penalty = harmonic_penalty(
        first_key,
        first_scale,
        second_key,
        second_scale
    )

    if penalty == 0.5:
        return "Relative major/minor"

    if first_key == second_key:
        return "Same tonic, different scale"

    if first_scale == second_scale:
        return "Same scale, different key"

    return "Different key and scale"


# --------------------------------------------------
# GET CANDIDATE TRACKS
# --------------------------------------------------

def get_candidates(
    occasion,
    selected_pools,
    include_seasonal
):

    profile = PROFILES[occasion]

    connection = duckdb.connect(
        str(DATABASE_FILE),
        read_only=True
    )

    query = """
        SELECT DISTINCT
            t.recording_mbid,
            t.title,
            t.artist,
            t.length_seconds,
            t.bpm,
            t.musical_key,
            t.scale,
            t.danceability,

            (
                ABS(t.bpm - ?)
                +
                ABS(t.danceability - ?) * 20
            ) AS occasion_distance

        FROM tracks AS t
    """

    parameters = [
        profile["target_bpm"],
        profile["target_danceability"],
    ]

    if selected_pools:

        placeholders = ", ".join(
            ["?"] * len(selected_pools)
        )

        query += """
            INNER JOIN track_music_pools AS p
                ON t.recording_mbid =
                   p.recording_mbid
        """

        pool_filter = (
            f"AND p.music_pool "
            f"IN ({placeholders})"
        )

    else:
        pool_filter = ""

    query += f"""
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
        + profile["bpm_range"],
    ])

    if selected_pools:
        parameters.extend(
            selected_pools
        )

    result = connection.execute(
        query,
        parameters
    )

    columns = [
        description[0]
        for description
        in result.description
    ]

    rows = result.fetchall()

    connection.close()

    candidates = [
        dict(zip(columns, row))
        for row in rows
    ]

    # Seasonal filtering happens after the database query.
    # This keeps the contextual rule separate from the
    # core acoustic and music-pool filtering.
    if not include_seasonal:
        candidates = [
            track
            for track in candidates
            if not is_seasonal_track(
                track["title"]
            )
        ]

    return candidates


# --------------------------------------------------
# CREATE SET
# --------------------------------------------------

def create_set(
    candidates,
    requested_minutes
):

    target_seconds = (
        requested_minutes * 60
    )

    selected_tracks = []
    selected_song_identities = set()

    total_seconds = 0

    # Candidates are already ranked by occasion
    # suitability.
    #
    # The same normalised artist/title combination
    # is not selected twice for one generated set.
    # Different MusicBrainz records remain untouched
    # in the underlying database.
    for track in candidates:

        if total_seconds >= target_seconds:
            break

        identity = song_identity(
            track
        )

        if identity in selected_song_identities:
            continue

        selected_tracks.append(
            track
        )

        selected_song_identities.add(
            identity
        )

        total_seconds += (
            track["length_seconds"]
        )

    if not selected_tracks:
        return [], 0

    remaining_tracks = (
        selected_tracks.copy()
    )

    first_track = min(
        remaining_tracks,
        key=lambda track: track["bpm"]
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

    return (
        ordered_tracks,
        total_seconds
    )


# --------------------------------------------------
# STREAMLIT PAGE
# --------------------------------------------------

st.set_page_config(
    page_title="SetFlow",
    page_icon="🎵",
    layout="wide",
)


st.title("SetFlow")

st.write(
    "Generate an explainable DJ-style set plan "
    "using music metadata and acoustic features."
)

st.caption(
    "SetFlow prioritises track suitability and "
    "transition characteristics. Requested duration "
    "is treated as a target rather than an exact cutoff."
)


# --------------------------------------------------
# USER CONTROLS
# --------------------------------------------------

st.subheader(
    "Build your set"
)


occasion = st.selectbox(
    "Occasion",
    list(PROFILES.keys())
)


requested_minutes = st.number_input(
    "Target duration (minutes)",
    min_value=10,
    max_value=240,
    value=30,
    step=5,
)


selected_pool_names = st.multiselect(
    "Music pools",
    list(MUSIC_POOLS.keys()),
    placeholder=(
        "Leave empty to use all music pools"
    ),
)


selected_pools = [
    MUSIC_POOLS[name]
    for name in selected_pool_names
]


include_seasonal = st.checkbox(
    "Include seasonal / Christmas music",
    value=False,
    help=(
        "By default, SetFlow filters tracks whose "
        "titles contain obvious Christmas or seasonal "
        "terms. This is a simple prototype contextual "
        "filter rather than a complete classification."
    ),
)


# --------------------------------------------------
# GENERATE BUTTON
# --------------------------------------------------

if st.button(
    "Generate Set",
    type="primary"
):

    if not DATABASE_FILE.exists():

        st.error(
            "SetFlow database not found. "
            "Run the data pipeline first."
        )

        st.stop()


    candidates = get_candidates(
        occasion,
        selected_pools,
        include_seasonal
    )


    if not candidates:

        st.warning(
            "No tracks matched this combination. "
            "Try another occasion or music pool."
        )

        st.stop()


    ordered_tracks, total_seconds = (
        create_set(
            candidates,
            requested_minutes
        )
    )


    actual_minutes = (
        total_seconds / 60
    )


    # ----------------------------------------------
    # SUMMARY
    # ----------------------------------------------

    st.success(
        "Set generated successfully."
    )


    column_one, column_two, column_three = (
        st.columns(3)
    )


    column_one.metric(
        "Tracks",
        len(ordered_tracks)
    )


    column_two.metric(
        "Approx. duration",
        f"{actual_minutes:.1f} min"
    )


    column_three.metric(
        "Candidates considered",
        len(candidates)
    )


    # ----------------------------------------------
    # TRACK TABLE
    # ----------------------------------------------

    st.subheader(
        "Your SetFlow plan"
    )


    table_rows = []


    for index, track in enumerate(
        ordered_tracks,
        start=1
    ):

        table_rows.append({
            "#": index,

            "Artist": track[
                "artist"
            ],

            "Track": track[
                "title"
            ],

            "BPM": round(
                track["bpm"],
                1
            ),

            "Key": (
                f"{track['musical_key']} "
                f"{track['scale']}"
            ),

            "Danceability": round(
                track["danceability"],
                3
            ),
        })


    st.dataframe(
        pd.DataFrame(
            table_rows
        ),
        hide_index=True,
        width="stretch",
    )


    # ----------------------------------------------
    # TRANSITION SUGGESTIONS
    # ----------------------------------------------

    if len(ordered_tracks) > 1:

        st.subheader(
            "Suggested transitions"
        )


        for index in range(
            len(ordered_tracks) - 1
        ):

            current_track = (
                ordered_tracks[index]
            )

            next_track = (
                ordered_tracks[
                    index + 1
                ]
            )

            bpm_change = (
                next_track["bpm"]
                - current_track["bpm"]
            )

            harmonic_description = (
                explain_harmonic_transition(
                    current_track,
                    next_track
                )
            )

            score = transition_score(
                current_track,
                next_track
            )


            with st.expander(
                (
                    f"{index + 1}. "
                    f"{current_track['artist']} – "
                    f"{current_track['title']} "
                    f"→ "
                    f"{next_track['artist']} – "
                    f"{next_track['title']}"
                )
            ):

                st.write(
                    f"**BPM change:** "
                    f"{bpm_change:+.1f}"
                )

                st.write(
                    f"**Harmonic relationship:** "
                    f"{harmonic_description}"
                )

                st.write(
                    f"**Transition score:** "
                    f"{score:.2f}"
                )


    st.caption(
        "Transition suggestions use transparent, "
        "rule-based acoustic heuristics and are not "
        "claims of objectively optimal mixes."
    )


# --------------------------------------------------
# HOW SETFLOW WORKS
# --------------------------------------------------

st.divider()

with st.expander(
    "How does SetFlow choose tracks?"
):

    st.write(
        """
SetFlow first filters tracks using the selected music
pools and an occasion-specific BPM range. Tracks are then
ranked using their distance from the occasion's target BPM
and danceability.

It selects suitable tracks until the requested duration is
reached or exceeded, while avoiding repeated normalised
artist-and-title combinations within the same set. The
selected tracks are then ordered using a transparent
transition heuristic based on BPM change, musical-key
relationships and danceability change.

The requested duration is therefore a target rather than an
exact cutoff. SetFlow currently prioritises track suitability
over forcing the set to an exact length.

The seasonal-music option is a simple contextual prototype.
When seasonal music is disabled, obvious seasonal terms in
track titles are filtered out. It is not intended to be a
complete semantic classification of music.
        """
    )