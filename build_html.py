#!/usr/bin/env python3
"""Build the SCOZ News digest from canonical weekly editions."""

import os
import sys

from news_archive import ArchiveError, load_archive
from news_publication import prepare_publication, print_guidelines

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "index.html")
CACHE_PATH = os.path.join(BASE_DIR, "noticias-cache.json")
DATA_DIR = os.path.join(BASE_DIR, "data")


def main() -> int:
    if "--guidelines" in sys.argv:
        print_guidelines()
        return 0

    try:
        archive = load_archive(DATA_DIR)
    except ArchiveError as error:
        print(f"Erro no arquivo de edições: {error}", file=sys.stderr)
        return 1

    if "--missing-weeks" in sys.argv:
        for week_id in archive.missing_recent_week_ids:
            print(week_id)
        return 0

    data = archive.to_render_data()
    print(f"Dados: {len(data['weeks'])} edição(ões) canônica(s) em data/")
    if archive.missing_recent_week_ids:
        missing = ", ".join(archive.missing_recent_week_ids)
        print(f"\n⚠  Lacunas editoriais recentes: {missing}")
    if archive.warnings:
        print(f"\n⚠  {len(archive.warnings)} shortfall(s) editorial(is):")
        for warning in archive.warnings:
            print(f"  • {warning}")
        print()

    output_path = HTML_PATH
    if "--output" in sys.argv:
        index = sys.argv.index("--output")
        if index + 1 >= len(sys.argv):
            print("Erro: --output exige um caminho.", file=sys.stderr)
            return 2
        output_path = sys.argv[index + 1]

    publication = prepare_publication(data)
    publication.write(output_path, CACHE_PATH)

    total = sum(
        len(category_items)
        for week in data["weeks"]
        for category_items in week["items"].values()
    )
    print(
        f"OK — {len(data['weeks'])} edição(ões), "
        f"{total} notícias → {output_path}"
    )
    print(f"Cache → {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
