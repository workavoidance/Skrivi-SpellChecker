"""Cache the pinned Bokmal portion of the Oslo-Bergen Multitagger."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
import zipfile

from obt_resources import MANIFEST, RESOURCE_ROOT, REVISION, SOURCE_DIR
from setup_assets import digest


URL = f"https://github.com/textlab/mtag/archive/{REVISION}.zip"
ARCHIVE_NAME = f"mtag-{REVISION[:8]}.zip"
SHA256 = "7d25d8463ace2edd514f51d4eec9cfe2926586c7c84baf1acbd2144831e116f5"
REQUIRED = ("mtag.py", "fullform_bm.py", "root_bm.py", "compounds_bm.py", "LICENSE")


def fetch() -> Path:
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    archive = RESOURCE_ROOT / ARCHIVE_NAME
    if archive.exists() and digest(archive) == SHA256:
        print(f"Reusing {ARCHIVE_NAME}", flush=True)
        return archive
    if archive.exists():
        raise RuntimeError(f"Cached archive failed its checksum: {archive}")
    partial = archive.with_suffix(".partial.zip")
    request = urllib.request.Request(URL, headers={"User-Agent": "Skrivi-POC/1"})
    print(f"Downloading {ARCHIVE_NAME} (about 26 MB)", flush=True)
    with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as target:
        while block := response.read(1024 * 1024):
            target.write(block)
    if digest(partial) != SHA256:
        partial.unlink(missing_ok=True)
        raise RuntimeError("Downloaded OBT checksum did not match.")
    partial.replace(archive)
    return archive


def install(archive: Path) -> None:
    temporary = Path(tempfile.mkdtemp(prefix="skrivi-obt-", dir=RESOURCE_ROOT))
    try:
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            for filename in REQUIRED:
                member = next((name for name in names if PurePosixPath(name).name == filename
                               and len(PurePosixPath(name).parts) == 2), None)
                if not member:
                    raise RuntimeError(f"OBT archive is missing {filename}")
                with bundle.open(member) as source, (temporary / filename).open("wb") as target:
                    shutil.copyfileobj(source, target)
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        for filename in REQUIRED:
            (temporary / filename).replace(SOURCE_DIR / filename)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def main() -> None:
    archive = fetch()
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    if existing.get("revision") == REVISION and all((SOURCE_DIR / name).exists() for name in REQUIRED):
        print("Reusing extracted Bokmal analyser", flush=True)
        return
    install(archive)
    files = {name: {"bytes": (SOURCE_DIR / name).stat().st_size,
                    "sha256": digest(SOURCE_DIR / name)} for name in REQUIRED}
    manifest = {
        "source": "https://github.com/textlab/mtag",
        "revision": REVISION,
        "archive_url": URL,
        "archive_sha256": SHA256,
        "archive_bytes": archive.stat().st_size,
        "installed_bytes": sum(item["bytes"] for item in files.values()),
        "code_license": "MIT",
        "lexical_data_license": "CC BY 4.0",
        "files": files,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"archive_bytes": manifest["archive_bytes"],
                      "installed_bytes": manifest["installed_bytes"]}), flush=True)
    print("OBT Bokmal compound analyser ready. Normal use is offline.", flush=True)


if __name__ == "__main__":
    main()

