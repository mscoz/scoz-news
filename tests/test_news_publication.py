import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from news_publication import Publication, prepare_publication


class PublicationContractTests(unittest.TestCase):
    def test_invalid_cache_never_replaces_existing_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "index.html"
            cache_path = root / "noticias-cache.json"
            html_path.write_text("publicação anterior", encoding="utf-8")
            cache_path.write_text('{"previous": true}', encoding="utf-8")

            with self.assertRaises(TypeError):
                Publication(
                    html="publicação nova",
                    cache={"invalid": object()},
                ).write(html_path, cache_path)

            self.assertEqual(
                html_path.read_text(encoding="utf-8"),
                "publicação anterior",
            )
            self.assertEqual(
                cache_path.read_text(encoding="utf-8"),
                '{"previous": true}',
            )

    def test_html_commit_failure_restores_the_previous_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "index.html"
            cache_path = root / "noticias-cache.json"
            html_path.write_text("publicação anterior", encoding="utf-8")
            cache_path.write_text('{"previous": true}', encoding="utf-8")
            real_replace = os.replace

            def fail_html_commit(source, destination):
                if Path(destination) == html_path:
                    raise OSError("falha simulada")
                real_replace(source, destination)

            with patch(
                "news_publication.os.replace",
                side_effect=fail_html_commit,
            ):
                with self.assertRaisesRegex(OSError, "falha simulada"):
                    Publication(
                        html="publicação nova",
                        cache={"previous": False},
                    ).write(html_path, cache_path)

            self.assertEqual(
                html_path.read_text(encoding="utf-8"),
                "publicação anterior",
            )
            self.assertEqual(
                cache_path.read_text(encoding="utf-8"),
                '{"previous": true}',
            )

    def test_prepares_html_and_cache_from_the_same_validated_data(self) -> None:
        data = {
            "weeks": [
                {
                    "id": "2026-07-27",
                    "items": {
                        "meta": [
                            {
                                "title": "Notícia única",
                                "source": "Fonte",
                                "date": "Jul 27, 2026",
                                "url": "https://example.com/noticia",
                                "summary": "Resumo verificado.",
                            }
                        ],
                        "google": [],
                        "ppc": [],
                        "mkt": [],
                        "ia": [],
                    },
                }
            ]
        }

        publication = prepare_publication(data)

        self.assertIn("Notícia única", publication.html)
        self.assertEqual(publication.cache["last_week_id"], "2026-07-27")
        self.assertEqual(
            publication.cache["seen_urls"],
            ["https://example.com/noticia"],
        )


if __name__ == "__main__":
    unittest.main()
