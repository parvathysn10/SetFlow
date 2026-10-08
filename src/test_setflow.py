
import ast
import unittest
from pathlib import Path


# Load the actual functions from app.py without launching
# the Streamlit interface.
APP_FILE = Path(__file__).with_name("app.py")

FUNCTION_NAMES = {
    "is_seasonal_track",
    "normalise_song_text",
    "song_identity",
    "circular_key_distance",
    "harmonic_penalty",
    "transition_score",
}

CONSTANT_NAMES = {
    "SEASONAL_TITLE_KEYWORDS",
    "PITCH_CLASSES",
}

source = ast.parse(
    APP_FILE.read_text(encoding="utf-8")
)

selected_nodes = [
    node
    for node in source.body
    if (
        isinstance(node, ast.FunctionDef)
        and node.name in FUNCTION_NAMES
    )
    or (
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id in CONSTANT_NAMES
            for target in node.targets
        )
    )
]

namespace = {"re": __import__("re")}

exec(
    compile(
        ast.Module(body=selected_nodes, type_ignores=[]),
        str(APP_FILE),
        "exec",
    ),
    namespace,
)

is_seasonal_track = namespace["is_seasonal_track"]
song_identity = namespace["song_identity"]
transition_score = namespace["transition_score"]


class TestSetFlow(unittest.TestCase):

    def test_duplicate_song_identity(self):
        first = {
            "artist": "SZA",
            "title": "ICE.MOON",
        }

        second = {
            "artist": "SZA",
            "title": "Ice Moon",
        }

        self.assertEqual(
            song_identity(first),
            song_identity(second),
        )

    def test_seasonal_filter(self):
        self.assertTrue(
            is_seasonal_track("Wit It This Christmas")
        )

        self.assertFalse(
            is_seasonal_track("Wasted Times")
        )

    def test_transition_scoring(self):
        first = {
            "bpm": 120,
            "musical_key": "C",
            "scale": "major",
            "danceability": 1.0,
        }

        similar = {
            "bpm": 122,
            "musical_key": "C",
            "scale": "major",
            "danceability": 1.0,
        }

        different = {
            "bpm": 150,
            "musical_key": "F#",
            "scale": "minor",
            "danceability": 0.3,
        }

        self.assertLess(
            transition_score(first, similar),
            transition_score(first, different),
        )


if __name__ == "__main__":
    unittest.main()
