import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from news_archive import ArchiveError, load_archive


CATEGORIES = ("meta", "google", "ppc", "mkt", "ia")


def item(title: str, published: str, url: str) -> dict[str, str]:
    return {
        "title": title,
        "source": "Fonte",
        "date": published,
        "url": url,
        "summary": "Resumo verificado.",
    }


def write_week(root: Path, week_id: str, items_by_category: dict | None = None, **extra) -> None:
    payload = {
        "schema_version": 1,
        "id": week_id,
        "label": "semana",
        "label_full": "Semana completa",
        "items": {category: [] for category in CATEGORIES},
        **extra,
    }
    if payload["schema_version"] is None:
        del payload["schema_version"]
    if items_by_category:
        payload["items"].update(items_by_category)
    (root / f"{week_id}.json").write_text(json.dumps(payload), encoding="utf-8")


class ArchiveContractTests(unittest.TestCase):
    def test_loads_canonical_editions_newest_first_for_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(
                root,
                "2026-07-20",
                {"meta": [item("Anterior", "Jul 20, 2026", "https://example.com/old")]},
            )
            write_week(
                root,
                "2026-07-27",
                {"meta": [item("Recente", "Jul 27, 2026", "https://example.com/new")]},
            )

            archive = load_archive(root, as_of=date(2026, 8, 3))

            self.assertEqual(
                [week["id"] for week in archive.to_render_data()["weeks"]],
                ["2026-07-27", "2026-07-20"],
            )
            self.assertEqual(archive.missing_recent_week_ids, ())

    def test_render_data_cannot_mutate_the_validated_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(root, "2026-07-27")
            archive = load_archive(root, as_of=date(2026, 8, 3))

            rendered = archive.to_render_data()
            rendered["weeks"][0]["id"] = "invalid"

            self.assertEqual(
                archive.to_render_data()["weeks"][0]["id"],
                "2026-07-27",
            )

    def test_rejects_an_edition_that_is_not_identified_by_its_monday(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(root, "2026-07-28")

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-28.json: id must be the edition Monday 2026-07-27",
            ):
                load_archive(root, as_of=date(2026, 8, 3))

    def test_rejects_a_repeated_url_in_a_later_edition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repeated_url = "https://example.com/repeated"
            write_week(
                root,
                "2026-07-20",
                {"meta": [item("Original", "Jul 20, 2026", repeated_url)]},
            )
            write_week(
                root,
                "2026-07-27",
                {"google": [item("Repetida", "Jul 27, 2026", repeated_url)]},
            )

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-27.json: repeated URL from 2026-07-20.json",
            ):
                load_archive(root, as_of=date(2026, 8, 3))

    def test_rejects_an_undocumented_repeat_in_legacy_editions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repeated_url = "https://example.com/legacy-repeat"
            write_week(
                root,
                "2026-05-04",
                {"meta": [item("Original", "May 4, 2026", repeated_url)]},
                schema_version=None,
            )
            write_week(
                root,
                "2026-05-11",
                {"meta": [item("Repetida", "May 11, 2026", repeated_url)]},
                schema_version=None,
            )

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-05-11.json: repeated URL from 2026-05-04.json",
            ):
                load_archive(root, as_of=date(2026, 5, 18))

    def test_allows_a_documented_repeat_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repeated_url = "https://example.com/follow-up"
            write_week(
                root,
                "2026-07-20",
                {"meta": [item("Original", "Jul 20, 2026", repeated_url)]},
            )
            write_week(
                root,
                "2026-07-27",
                {"meta": [item("Follow-up", "Jul 27, 2026", repeated_url)]},
                repeat_url_overrides=[repeated_url],
            )

            archive = load_archive(root, as_of=date(2026, 8, 3))

            self.assertEqual(len(archive.to_render_data()["weeks"]), 2)

    def test_rejects_a_publication_date_outside_its_edition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(
                root,
                "2026-07-27",
                {
                    "meta": [
                        item(
                            "Fora da janela",
                            "Aug 3, 2026",
                            "https://example.com/outside",
                        )
                    ]
                },
            )

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-27.json: Aug 3, 2026 is outside 2026-07-27..2026-08-02",
            ):
                load_archive(root, as_of=date(2026, 8, 3))

    def test_rejects_a_non_https_news_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(
                root,
                "2026-07-27",
                {"meta": [item("URL insegura", "Jul 27, 2026", "http://example.com")]},
            )

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-27.json: news URL must use HTTPS",
            ):
                load_archive(root, as_of=date(2026, 8, 3))

    def test_reports_only_the_two_most_recent_missing_editions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(root, "2026-07-06")

            archive = load_archive(root, as_of=date(2026, 8, 3))

            self.assertEqual(
                archive.missing_recent_week_ids,
                ("2026-07-27", "2026-07-20"),
            )

    def test_reports_completed_week_missing_before_a_future_edition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(root, "2026-08-03")

            archive = load_archive(root, as_of=date(2026, 8, 3))

            self.assertEqual(
                archive.missing_recent_week_ids,
                ("2026-07-27",),
            )

    def test_documents_category_shortfalls_without_rejecting_the_edition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(root, "2026-07-27")

            archive = load_archive(root, as_of=date(2026, 8, 3))

            self.assertIn(
                "[2026-07-27] meta: 0/10 verified items",
                archive.warnings,
            )

    def test_rejects_news_without_every_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            incomplete = item("Incompleta", "Jul 27, 2026", "https://example.com")
            del incomplete["summary"]
            write_week(root, "2026-07-27", {"meta": [incomplete]})

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-27.json: news item fields must be",
            ):
                load_archive(root, as_of=date(2026, 8, 3))


    def test_rejects_an_untranslated_english_title(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(
                root,
                "2026-07-27",
                {
                    "google": [
                        item(
                            "Google Ads Editor Version 2.13 Is Now Available",
                            "Jul 27, 2026",
                            "https://example.com/editor",
                        )
                    ]
                },
            )

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-27.json: title must be written in PT-BR",
            ):
                load_archive(root, as_of=date(2026, 8, 3))

    def test_rejects_an_untranslated_english_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            news = item(
                "Google apresenta nova versão do editor",
                "Jul 27, 2026",
                "https://example.com/editor",
            )
            news["summary"] = (
                "Google launches a new editor version with campaign improvements."
            )
            write_week(root, "2026-07-27", {"google": [news]})

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-27.json: summary must be written in PT-BR",
            ):
                load_archive(root, as_of=date(2026, 8, 3))

    def test_allows_product_names_inside_portuguese_editorial_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(
                root,
                "2026-07-27",
                {
                    "google": [
                        item(
                            "Google Ads testa carrossel de insights automatizados",
                            "Jul 27, 2026",
                            "https://example.com/insights",
                        )
                    ]
                },
            )

            archive = load_archive(root, as_of=date(2026, 8, 3))

            self.assertEqual(len(archive.to_render_data()["weeks"]), 1)

    def test_rejects_an_edition_without_the_canonical_categories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(root, "2026-07-27", items={"meta": []})

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-07-27.json: categories must be meta, google, ppc, mkt, ia",
            ):
                load_archive(root, as_of=date(2026, 8, 3))

    def test_merges_legacy_collisions_with_the_newer_filename_winning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repeated_url = "https://example.com/story"
            write_week(
                root,
                "2026-05-04",
                {"meta": [item("Versão antiga", "May 4, 2026", repeated_url)]},
                schema_version=None,
            )
            write_week(
                root,
                "2026-05-05",
                {"meta": [item("Versão nova", "May 5, 2026", repeated_url)]},
                schema_version=None,
            )

            archive = load_archive(root, as_of=date(2026, 5, 11))
            weeks = archive.to_render_data()["weeks"]

            self.assertEqual(len(weeks), 1)
            self.assertEqual(weeks[0]["id"], "2026-05-04")
            self.assertEqual(weeks[0]["items"]["meta"][0]["title"], "Versão nova")

    def test_newer_legacy_file_can_reclassify_a_repeated_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repeated_url = "https://example.com/reclassified"
            write_week(
                root,
                "2026-05-04",
                {"meta": [item("Meta", "May 4, 2026", repeated_url)]},
                schema_version=None,
            )
            write_week(
                root,
                "2026-05-05",
                {"google": [item("Google", "May 5, 2026", repeated_url)]},
                schema_version=None,
            )

            week = load_archive(
                root,
                as_of=date(2026, 5, 11),
            ).to_render_data()["weeks"][0]

            self.assertEqual(week["items"]["meta"], [])
            self.assertEqual(week["items"]["google"][0]["title"], "Google")

    def test_legacy_merge_preserves_overrides_for_retained_older_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repeated_url = "https://example.com/intentional-repeat"
            write_week(
                root,
                "2026-04-27",
                {"meta": [item("Primeira", "Apr 27, 2026", repeated_url)]},
                schema_version=None,
            )
            write_week(
                root,
                "2026-05-04",
                {"meta": [item("Follow-up", "May 4, 2026", repeated_url)]},
                schema_version=None,
                repeat_url_overrides=[repeated_url],
            )
            write_week(
                root,
                "2026-05-05",
                {
                    "google": [
                        item(
                            "Outra notícia",
                            "May 5, 2026",
                            "https://example.com/other",
                        )
                    ]
                },
                schema_version=None,
            )

            archive = load_archive(root, as_of=date(2026, 5, 11))

            self.assertEqual(len(archive.to_render_data()["weeks"]), 2)

    def test_rejects_a_post_cutover_edition_without_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_week(root, "2026-08-03", schema_version=None)

            with self.assertRaisesRegex(
                ArchiveError,
                "2026-08-03.json: schema_version 1 is required",
            ):
                load_archive(root, as_of=date(2026, 8, 10))


if __name__ == "__main__":
    unittest.main()
