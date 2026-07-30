import tempfile
import unittest
from pathlib import Path
from tomllib import loads

import benchwork
from benchwork.rites import RiteRegistry


class DistributionTest(unittest.TestCase):
    def test_package_and_project_versions_match(self) -> None:
        project = loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(benchwork.__version__, project["project"]["version"])
        self.assertEqual(benchwork.__version__, "0.3.0a1")

    def test_init_creates_both_versioned_registries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            RiteRegistry(root).initialize()
            self.assertTrue((root / ".benchwork" / "rites.json").is_file())
            self.assertTrue((root / ".benchwork" / "grimoires.json").is_file())
