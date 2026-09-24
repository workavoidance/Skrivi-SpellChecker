import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from obt_resources import ObtResources


class ObtResourcesTests(unittest.TestCase):
    def test_requires_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "Setup-OBT"):
                ObtResources(Path(directory))

    def test_worker_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("mtag.py", "fullform_bm.py", "root_bm.py", "compounds_bm.py"):
                (root / name).touch()
            completed = type("Run", (), {
                "returncode": 0,
                "stdout": json.dumps({"brettspill": {"strict": []}}),
                "stderr": "",
            })()
            with patch("obt_resources.subprocess.run", return_value=completed) as run:
                result = ObtResources(root).analyse(["Brettspill", "brettspill"])
            self.assertEqual(result, {"brettspill": {"strict": []}})
            payload = json.loads(run.call_args.kwargs["input"])
            self.assertEqual(payload, ["brettspill"])


if __name__ == "__main__":
    unittest.main()
