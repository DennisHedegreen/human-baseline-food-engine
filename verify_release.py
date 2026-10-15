"""Integrity check independent of optional local development dependencies."""
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/"release-manifest.json").read_text())
    expected=set()
    for item in manifest["files"]:
        rel=Path(item["path"])
        assert not rel.is_absolute() and ".." not in rel.parts and item["path"] not in expected
        expected.add(item["path"])
        path=root/rel
        assert path.is_file() and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"],rel
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
            and not any(part in {".git",".venv","__pycache__"} for part in p.relative_to(root).parts)
            and p.suffix not in {".pyc",".pyo"}}
    assert actual==expected|{"release-manifest.json"},actual^(expected|{"release-manifest.json"})
    lock=json.loads((root/"dependency-lock.json").read_text())
    for item in lock["files"]:
        assert hashlib.sha256((root/item["path"]).read_bytes()).hexdigest()==item["sha256"]
    print(f"Verified {manifest['release_version']}: {len(expected)} payload files; locked population dependency. Status: {manifest['status']}")


if __name__=="__main__": main()
