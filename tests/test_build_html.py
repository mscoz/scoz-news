import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_html import publish_outputs


class PublicationContractTests(unittest.TestCase):
    def test_invalid_cache_never_replaces_existing_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "index.html"
            cache_path = root / "noticias-cache.json"
            html_path.write_text("publicação anterior", encoding="utf-8")
            cache_path.write_text('{"previous": true}', encoding="utf-8")

            with self.assertRaises(TypeError):
                publish_outputs(
                    html_path,
                    "publicação nova",
                    cache_path,
                    {"invalid": object()},
                )

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

            with patch("build_html.os.replace", side_effect=fail_html_commit):
                with self.assertRaisesRegex(OSError, "falha simulada"):
                    publish_outputs(
                        html_path,
                        "publicação nova",
                        cache_path,
                        {"previous": False},
                    )

            self.assertEqual(
                html_path.read_text(encoding="utf-8"),
                "publicação anterior",
            )
            self.assertEqual(
                cache_path.read_text(encoding="utf-8"),
                '{"previous": true}',
            )


if __name__ == "__main__":
    unittest.main()
