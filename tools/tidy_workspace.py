"""Archive generated runs and installer leftovers without deleting user files."""
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    cache = root / ".cache"
    candidates = [(path, cache / "local-runs" / path.name)
                  for path in root.iterdir() if path.is_dir()
                  and (path.name == "output" or path.name.startswith("output-"))]
    candidates += [(path, cache / "setup-leftovers" / path.name)
                   for path in root.iterdir() if path.is_dir()
                   and path.name.startswith(("pip-", "tmp"))]
    for source, destination in candidates:
        # Resolve both ends and verify before any directory move on Windows.
        source = source.resolve()
        destination = destination.resolve()
        if source.parent != root or not destination.is_relative_to(cache.resolve()):
            raise ValueError("Archive path outside workspace")
        if destination.exists():
            print(f"Skipped (archive exists): {source.name}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            source.rename(destination)
            print(f"Archived: {source.name}")
        except OSError:
            print(f"Skipped (locked or inaccessible): {source.name}")


if __name__ == "__main__":
    main()
