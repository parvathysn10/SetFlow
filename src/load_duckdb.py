import json
from pathlib import Path

import duckdb


INPUT_FILE = Path(
    "data/processed/setflow_tracks.json"
)

DATABASE_FILE = Path(
    "data/setflow.duckdb"
)


# -----------------------------
# Load clean SetFlow JSON
# -----------------------------

with INPUT_FILE.open(
    "r",
    encoding="utf-8"
) as file:
    tracks = json.load(file)


print(
    "SetFlow tracks to load:",
    len(tracks)
)


# -----------------------------
# Connect to DuckDB
# -----------------------------

connection = duckdb.connect(
    str(DATABASE_FILE)
)


# -----------------------------
# Create the main tracks table
# -----------------------------

connection.execute(
    """
    CREATE OR REPLACE TABLE tracks (
        recording_mbid VARCHAR PRIMARY KEY,
        title VARCHAR,
        artist VARCHAR,
        length_seconds DOUBLE,
        bpm DOUBLE,
        musical_key VARCHAR,
        scale VARCHAR,
        danceability DOUBLE,
        average_loudness DOUBLE,
        dynamic_complexity DOUBLE,
        onset_rate DOUBLE,
        acoustic_length_seconds DOUBLE
    )
    """
)


# ---------------------------------------
# Create track-to-music-pool table
# ---------------------------------------

connection.execute(
    """
    CREATE OR REPLACE TABLE track_music_pools (
        recording_mbid VARCHAR,
        music_pool VARCHAR,
        PRIMARY KEY (
            recording_mbid,
            music_pool
        )
    )
    """
)


# -----------------------------
# Insert clean records
# -----------------------------

for track in tracks:

    connection.execute(
        """
        INSERT INTO tracks VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            track["recording_mbid"],
            track["title"],
            track["artist"],
            track["length_seconds"],
            track["bpm"],
            track["key"],
            track["scale"],
            track["danceability"],
            track["average_loudness"],
            track["dynamic_complexity"],
            track["onset_rate"],
            track["acoustic_length_seconds"]
        ]
    )

    for music_pool in track.get(
        "music_pools",
        []
    ):

        connection.execute(
            """
            INSERT INTO track_music_pools
            VALUES (?, ?)
            """,
            [
                track["recording_mbid"],
                music_pool
            ]
        )


# -----------------------------
# Validate the database
# -----------------------------

row_count = connection.execute(
    """
    SELECT COUNT(*)
    FROM tracks
    """
).fetchone()[0]


unique_mbids = connection.execute(
    """
    SELECT COUNT(
        DISTINCT recording_mbid
    )
    FROM tracks
    """
).fetchone()[0]


missing_bpm = connection.execute(
    """
    SELECT COUNT(*)
    FROM tracks
    WHERE bpm IS NULL
    """
).fetchone()[0]


missing_key = connection.execute(
    """
    SELECT COUNT(*)
    FROM tracks
    WHERE musical_key IS NULL
    """
).fetchone()[0]


artist_count = connection.execute(
    """
    SELECT COUNT(
        DISTINCT artist
    )
    FROM tracks
    """
).fetchone()[0]


pool_relationship_count = connection.execute(
    """
    SELECT COUNT(*)
    FROM track_music_pools
    """
).fetchone()[0]


tracks_without_pool = connection.execute(
    """
    SELECT COUNT(*)
    FROM tracks AS t
    LEFT JOIN track_music_pools AS p
        ON t.recording_mbid = p.recording_mbid
    WHERE p.recording_mbid IS NULL
    """
).fetchone()[0]


# ---------------------------------------
# Music pool coverage using SQL
# ---------------------------------------

pool_counts = connection.execute(
    """
    SELECT
        music_pool,
        COUNT(*) AS track_count
    FROM track_music_pools
    GROUP BY music_pool
    ORDER BY track_count DESC
    """
).fetchall()


# -----------------------------
# Show example SQL result
# -----------------------------

example_tracks = connection.execute(
    """
    SELECT
        artist,
        title,
        ROUND(bpm, 1) AS bpm,
        musical_key,
        scale,
        ROUND(danceability, 3)
            AS danceability
    FROM tracks
    ORDER BY danceability DESC
    LIMIT 10
    """
).fetchall()


print(
    "\n--- DuckDB validation summary ---"
)

print(
    "Rows in tracks table:",
    row_count
)

print(
    "Unique MBIDs:",
    unique_mbids
)

print(
    "Distinct artists:",
    artist_count
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
    "Track-pool relationships:",
    pool_relationship_count
)

print(
    "Tracks without a music pool:",
    tracks_without_pool
)


print(
    "\n--- Music pool coverage in DuckDB ---"
)

for pool, count in pool_counts:

    print(
        f"{pool}: {count}"
    )


print(
    "\n--- Example SQL query ---"
)

print(
    "10 tracks with highest "
    "danceability values:\n"
)


for row in example_tracks:

    print(
        f"{row[0]} - {row[1]} | "
        f"{row[2]} BPM | "
        f"{row[3]} {row[4]} | "
        f"danceability {row[5]}"
    )


connection.close()


print(
    "\nDuckDB database saved to:",
    DATABASE_FILE
)