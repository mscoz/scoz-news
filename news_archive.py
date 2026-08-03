"""Canonical weekly-edition archive for SCOZ News."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

CATEGORY_IDS = ("meta", "google", "ppc", "mkt", "ia")
MIN_ITEMS_PER_CATEGORY = 10
REQUIRED_ITEM_FIELDS = {"title", "source", "date", "url", "summary"}
SCHEMA_CUTOVER_ID = "2026-07-27"

ENGLISH_EDITORIAL_PATTERN = re.compile(
    r"\b(?:"
    r"adds|ads|and|available|brand|brings|building|carousel|content|conversions|"
    r"data|descriptions|effective|for|from|gets|global|guide|help|image|impact|"
    r"insights|intelligence|introduces|launches|marketing|measurement|new|now|"
    r"only|partner|performance|poor|powering|prepare|privacy|program|quality|"
    r"release|reports|risk|rollout|smarter|study|the|tips|to|transforms|upgrade|"
    r"using|version|ways|with"
    r")\b",
    re.IGNORECASE,
)
PORTUGUESE_EDITORIAL_PATTERN = re.compile(
    r"\b(?:"
    r"adiciona|amplia|anuncia|apresenta|atualiza|aos|começa|como|com|cria|das|"
    r"destaca|dos|enfrenta|entre|estudo|ganha|inclui|lança|leva|mais|marca|"
    r"mede|melhora|nova|novo|para|permite|podem|publica|remove|resumo|sem|"
    r"testa|traz|usa|versão|verificado"
    r")\b|[áàâãéêíóôõúç]",
    re.IGNORECASE,
)


def _looks_like_untranslated_english(text: object) -> bool:
    value = str(text)
    return bool(ENGLISH_EDITORIAL_PATTERN.search(value)) and not bool(
        PORTUGUESE_EDITORIAL_PATTERN.search(value)
    )


class ArchiveError(ValueError):
    """The canonical archive cannot be published."""


@dataclass(frozen=True)
class Archive:
    """Validated editions ready for publication through one interface."""

    _weeks: tuple[dict, ...]
    missing_recent_week_ids: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_render_data(self) -> dict[str, list[dict]]:
        return {"weeks": deepcopy(list(self._weeks))}


def _previous_completed_monday(as_of: date) -> date:
    current_monday = as_of - timedelta(days=as_of.weekday())
    return current_monday - timedelta(days=7)


def _merge_legacy_weeks(older: dict, newer: dict, canonical_id: str) -> dict:
    newer_urls = {
        item.get("url")
        for category in CATEGORY_IDS
        for item in newer["items"].get(category, ())
        if item.get("url")
    }
    merged_items = {
        category: [
            item
            for item in older["items"].get(category, ())
            if item.get("url") not in newer_urls
        ]
        + list(newer["items"].get(category, ()))
        for category in CATEGORY_IDS
    }
    merged = dict(newer)
    merged["id"] = canonical_id
    merged["items"] = merged_items
    merged["repeat_url_overrides"] = list(
        dict.fromkeys(
            [
                *older.get("repeat_url_overrides", ()),
                *newer.get("repeat_url_overrides", ()),
            ]
        )
    )
    return merged


def load_archive(data_dir: str | Path, *, as_of: date | None = None) -> Archive:
    """Load the canonical archive, newest edition first."""

    root = Path(data_dir)
    warnings = []
    loaded_by_id: dict[str, tuple[Path, dict]] = {}
    for path in sorted(root.glob("????-??-??.json")):
        week = json.loads(path.read_text(encoding="utf-8"))
        week_id = week.get("id")
        try:
            week_date = date.fromisoformat(week_id)
        except (TypeError, ValueError) as error:
            raise ArchiveError(f"{path.name}: invalid id {week_id!r}") from error
        monday = week_date - timedelta(days=week_date.weekday())
        canonical_id = monday.isoformat()
        schema_version = week.get("schema_version")
        if schema_version not in (None, 1):
            raise ArchiveError(
                f"{path.name}: unsupported schema_version {schema_version!r}"
            )
        if canonical_id >= SCHEMA_CUTOVER_ID and schema_version != 1:
            raise ArchiveError(f"{path.name}: schema_version 1 is required")
        strict = schema_version == 1
        if strict and week_id != canonical_id:
            raise ArchiveError(
                f"{path.name}: id must be the edition Monday {canonical_id}"
            )
        if strict and path.stem != week_id:
            raise ArchiveError(f"{path.name}: filename must match id {week_id}")
        items = week.get("items")
        if not isinstance(items, dict) or set(items) != set(CATEGORY_IDS):
            raise ArchiveError(
                f"{path.name}: categories must be {', '.join(CATEGORY_IDS)}"
            )
        if strict:
            edition_end = week_date + timedelta(days=6)
            for category_items in items.values():
                for item in category_items:
                    if set(item) != REQUIRED_ITEM_FIELDS:
                        expected_fields = ", ".join(sorted(REQUIRED_ITEM_FIELDS))
                        raise ArchiveError(
                            f"{path.name}: news item fields must be {expected_fields}"
                        )
                    for field in ("title", "summary"):
                        if _looks_like_untranslated_english(item[field]):
                            raise ArchiveError(
                                f"{path.name}: {field} must be written in PT-BR"
                            )
                    published_label = item.get("date", "")
                    try:
                        published = datetime.strptime(
                            published_label, "%b %d, %Y"
                        ).date()
                    except (TypeError, ValueError) as error:
                        raise ArchiveError(
                            f"{path.name}: invalid publication date {published_label!r}"
                        ) from error
                    if not week_date <= published <= edition_end:
                        raise ArchiveError(
                            f"{path.name}: {published_label} is outside "
                            f"{week_id}..{edition_end.isoformat()}"
                        )
                    url = item.get("url", "")
                    parsed_url = urlsplit(url)
                    if parsed_url.scheme != "https" or not parsed_url.netloc:
                        raise ArchiveError(
                            f"{path.name}: news URL must use HTTPS: {url}"
                        )
            for category in CATEGORY_IDS:
                count = len(items[category])
                if count < MIN_ITEMS_PER_CATEGORY:
                    warnings.append(
                        f"[{week_id}] {category}: {count}/"
                        f"{MIN_ITEMS_PER_CATEGORY} verified items"
                    )
        week["id"] = canonical_id
        existing = loaded_by_id.get(canonical_id)
        if existing is not None:
            _, older_week = existing
            week = _merge_legacy_weeks(older_week, week, canonical_id)
        loaded_by_id[canonical_id] = (path, week)

    loaded = sorted(loaded_by_id.values(), key=lambda pair: pair[1]["id"], reverse=True)

    seen_urls: dict[str, Path] = {}
    for path, week in reversed(loaded):
        overrides = set(week.get("repeat_url_overrides", ()))
        for category_items in week.get("items", {}).values():
            for item in category_items:
                url = item.get("url", "")
                previous_path = seen_urls.get(url)
                if previous_path is not None and url not in overrides:
                    raise ArchiveError(
                        f"{path.name}: repeated URL from {previous_path.name}: {url}"
                    )
                if url:
                    seen_urls[url] = path

    weeks = [week for _, week in loaded]
    expected_date = _previous_completed_monday(as_of or date.today())
    present_dates = {date.fromisoformat(week["id"]) for week in weeks}
    if present_dates:
        lower_bound = min(min(present_dates), expected_date)
        candidate = expected_date
        missing_dates = []
        while candidate >= lower_bound and len(missing_dates) < 2:
            if candidate not in present_dates:
                missing_dates.append(candidate.isoformat())
            candidate -= timedelta(days=7)
        missing = tuple(missing_dates)
    else:
        missing = (expected_date.isoformat(),)
    return Archive(tuple(weeks), missing, tuple(warnings))
