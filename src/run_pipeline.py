import subprocess
import sys
from pathlib import Path


# -----------------------------
# SetFlow pipeline stages
# -----------------------------

PIPELINE_STAGES = [
    (
        "Transform MusicBrainz catalogue",
        "transform_catalogue.py"
    ),
    (
        "Transform AcousticBrainz data",
        "transform_acousticbrainz.py"
    ),
    (
        "Join music datasets",
        "join_music_data.py"
    ),
    (
        "Validate processed data",
        "validate_data.py"
    ),
    (
        "Load data into DuckDB",
        "load_duckdb.py"
    ),
]


SCRIPT_DIRECTORY = Path(__file__).parent


# -----------------------------
# Run pipeline
# -----------------------------

print(
    "\n========================================"
)

print(
    "SetFlow data pipeline"
)

print(
    "========================================\n"
)


for stage_number, (
    stage_name,
    script_name
) in enumerate(
    PIPELINE_STAGES,
    start=1
):

    script_path = (
        SCRIPT_DIRECTORY
        / script_name
    )

    print(
        "\n----------------------------------------"
    )

    print(
        f"Stage {stage_number}/"
        f"{len(PIPELINE_STAGES)}: "
        f"{stage_name}"
    )

    print(
        "----------------------------------------\n"
    )


    result = subprocess.run(
        [
            sys.executable,
            str(script_path)
        ]
    )


    if result.returncode != 0:

        print(
            "\n========================================"
        )

        print(
            "PIPELINE FAILED"
        )

        print(
            "========================================"
        )

        print(
            f"Stage failed: {stage_name}"
        )

        print(
            "Later stages were not run."
        )

        sys.exit(
            result.returncode
        )


    print(
        f"\nCompleted: {stage_name}"
    )


# -----------------------------
# Final result
# -----------------------------

print(
    "\n========================================"
)

print(
    "PIPELINE COMPLETED SUCCESSFULLY"
)

print(
    "========================================"
)

print(
    f"All {len(PIPELINE_STAGES)} "
    "stages completed."
)

print(
    "Processed data has been validated "
    "and loaded into DuckDB."
)