from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.RAG.vectorStoreService import VectorStoreService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import local papers into the vector database.")
    parser.add_argument(
        "files",
        nargs="*",
        help="Optional file paths. If omitted, files under data_path in .env are imported.",
    )
    parser.add_argument("--reset", action="store_true", help="Clear the collection before importing.")
    parser.add_argument("--reindex", action="store_true", help="Rebuild selected files even if their MD5 exists.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = VectorStoreService().load_document(
        file_paths=args.files or None,
        reset=args.reset,
        reindex=args.reindex,
    )
    print(
        "Import finished: "
        f"total={stats['total']}, loaded={stats['loaded']}, "
        f"skipped={stats['skipped']}, failed={stats['failed']}"
    )


if __name__ == "__main__":
    main()