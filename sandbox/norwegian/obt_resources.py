"""Offline access to the Oslo-Bergen Multitagger compound analyser."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from setup_assets import ROOT


REVISION = "12291ffdf707c60d6918ac417aaedb7357176897"
RESOURCE_ROOT = ROOT / "lexical" / f"obt-mtag-{REVISION[:8]}"
SOURCE_DIR = RESOURCE_ROOT / "source"
MANIFEST = RESOURCE_ROOT / "manifest.json"
BRIDGE = Path(__file__).with_name("obt_worker.py")


class ObtResources:
    def __init__(self, source_dir: Path = SOURCE_DIR):
        self.source_dir = Path(source_dir)
        required = ("mtag.py", "fullform_bm.py", "root_bm.py", "compounds_bm.py")
        missing = [name for name in required if not (self.source_dir / name).exists()]
        if missing:
            raise RuntimeError("Run Setup-OBT.cmd once to enable this experiment.")

    def analyse(self, words) -> dict[str, dict]:
        requested = list(dict.fromkeys(str(word).casefold() for word in words if str(word).strip()))
        if not requested:
            return {}
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        run = subprocess.run(
            [sys.executable, str(BRIDGE), str(self.source_dir)],
            input=json.dumps(requested, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=environment,
            check=False,
        )
        if run.returncode:
            raise RuntimeError(f"OBT analyser failed: {run.stderr.strip()}")
        return json.loads(run.stdout)

    def metadata(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
