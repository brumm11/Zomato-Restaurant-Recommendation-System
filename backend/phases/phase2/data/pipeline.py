from __future__ import annotations

import json
import re
import csv
from io import StringIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from datasets import DatasetDict, load_dataset

from backend.phases.phase1.core.config import settings
from backend.phases.phase1.core.logging import get_logger
from backend.phases.phase2.data.models import DataQualityReport, NormalizedRestaurant

logger = get_logger(__name__)

CITY_ALIASES = {
    "bengaluru": "bangalore",
    "bangalore": "bangalore",
    "new delhi": "delhi",
    "ncr": "delhi",
    "bombay": "mumbai",
}
KNOWN_CITIES = {"bangalore", "bengaluru", "delhi", "new delhi", "mumbai", "hyderabad", "chennai", "pune", "kolkata"}

EXPECTED_FIELDS = {
    "name": ["restaurant_name", "name"],
    "city": ["location", "city"],
    "area": ["locality", "area", "address"],
    "cuisines": ["cuisines", "cuisine"],
    "avg_cost_for_two": [
        "average_cost_for_two",
        "cost_for_two",
        "price_for_two",
        "cost",
        "approx_cost(for two people)",
        "average_cost",
    ],
    "rating": ["aggregate_rating", "rating", "rate"],
    "votes": ["votes"],
}


def run_ingestion(output_dir: str = "artifacts/data") -> DataQualityReport:
    dataset_name = _extract_dataset_name(settings.data_source)
    logger.info("Starting ingestion for source=%s", dataset_name)

    raw_records = _load_records(dataset_name)
    now = datetime.now(timezone.utc)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rows_seen = 0
    rows_written = 0
    dropped_missing_name_or_city = 0
    duplicate_rows_removed = 0
    null_rating_count = 0

    dedupe_keys: set[tuple[str, str, str | None, tuple[str, ...]]] = set()
    normalized_rows: list[NormalizedRestaurant] = []

    for row in raw_records:
        rows_seen += 1
        normalized = _normalize_record(row, source_last_updated=now)
        if normalized is None:
            dropped_missing_name_or_city += 1
            continue

        if normalized.rating is None:
            null_rating_count += 1

        key = (
            normalized.name.lower(),
            normalized.city.lower(),
            normalized.area.lower() if normalized.area else None,
            tuple(sorted(c.lower() for c in normalized.cuisines)),
        )
        if key in dedupe_keys:
            duplicate_rows_removed += 1
            continue

        dedupe_keys.add(key)
        normalized_rows.append(normalized)
        rows_written += 1

    normalized_file = output_path / "restaurants_normalized.jsonl"
    report_file = output_path / "data_quality_report.json"

    with normalized_file.open("w", encoding="utf-8") as f:
        for item in normalized_rows:
            f.write(json.dumps(item.model_dump(mode="json"), ensure_ascii=True))
            f.write("\n")

    report = DataQualityReport(
        source=dataset_name,
        rows_seen=rows_seen,
        rows_written=rows_written,
        dropped_missing_name_or_city=dropped_missing_name_or_city,
        duplicate_rows_removed=duplicate_rows_removed,
        null_rating_count=null_rating_count,
    )
    report_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    logger.info(
        "Ingestion complete rows_seen=%s rows_written=%s dropped=%s duplicates=%s",
        rows_seen,
        rows_written,
        dropped_missing_name_or_city,
        duplicate_rows_removed,
    )
    return report


def _extract_dataset_name(data_source: str) -> str:
    if ":" in data_source:
        return data_source.split(":", 1)[1]
    return data_source


def _load_records(dataset_name: str) -> list[dict[str, Any]]:
    try:
        loaded = load_dataset(dataset_name)
        if isinstance(loaded, DatasetDict):
            split = "train" if "train" in loaded else next(iter(loaded.keys()))
            ds = loaded[split]
        else:
            ds = loaded
        return [dict(record) for record in ds]
    except Exception:
        logger.exception("Primary dataset load failed, attempting CSV URL fallback")
        return _load_records_from_csv_fallback(dataset_name)


def _load_records_from_csv_fallback(dataset_name: str) -> list[dict[str, Any]]:
    # Fallback for environments where HF cache/path resolution intermittently fails on Windows.
    url = f"https://huggingface.co/datasets/{dataset_name}/resolve/main/zomato.csv"
    csv.field_size_limit(10_000_000)
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        text = response.text
    reader = csv.DictReader(StringIO(text))
    return [dict(row) for row in reader]


def _normalize_record(row: dict[str, Any], source_last_updated: datetime) -> NormalizedRestaurant | None:
    name = _as_text(_pick(row, "name"))
    city = _normalize_city(_as_text(_pick(row, "city")))
    if not name or not city:
        return None

    area = _as_text(_pick(row, "area"))
    cuisines = _normalize_cuisines(_pick(row, "cuisines"))
    avg_cost_for_two = _parse_float(_pick(row, "avg_cost_for_two"))
    rating = _clamp_rating(_parse_float(_pick(row, "rating")))
    votes = _parse_int(_pick(row, "votes"))
    budget_tier = _derive_budget_tier(avg_cost_for_two)
    tags = _build_tags(row)

    restaurant_id = _as_text(row.get("restaurant_id")) or _stable_id(name, city, area)

    return NormalizedRestaurant(
        restaurant_id=restaurant_id,
        name=name,
        city=city,
        area=area,
        cuisines=cuisines,
        avg_cost_for_two=avg_cost_for_two,
        budget_tier=budget_tier,
        rating=rating,
        votes=votes,
        tags=tags,
        source_last_updated=source_last_updated,
    )


def _pick(row: dict[str, Any], logical_key: str) -> Any:
    for key in EXPECTED_FIELDS.get(logical_key, []):
        if key in row:
            return row.get(key)
    return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _normalize_city(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower()
    # Many records store full addresses/localities in "location"; extract known city when present.
    for city in KNOWN_CITIES:
        if city in lowered:
            return CITY_ALIASES.get(city, city)
    if "," in lowered:
        tail = lowered.split(",")[-1].strip()
        if tail:
            return CITY_ALIASES.get(tail, tail)
    return CITY_ALIASES.get(lowered, lowered)


def _normalize_cuisines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        parts = [str(v).strip().lower() for v in value if str(v).strip()]
    else:
        parts = [p.strip().lower() for p in str(value).split(",") if p.strip()]
    seen: set[str] = set()
    result: list[str] = []
    for item in parts:
        canonical = item.replace("  ", " ").replace(" ", "-")
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def _parse_int(value: Any) -> int | None:
    number = _parse_float(value)
    if number is None:
        return None
    return int(number)


def _clamp_rating(value: float | None) -> float | None:
    if value is None:
        return None
    if value < 0:
        return 0.0
    if value > 5:
        return 5.0
    return round(value, 1)


def _derive_budget_tier(avg_cost_for_two: float | None) -> str | None:
    if avg_cost_for_two is None:
        return None
    if avg_cost_for_two <= 800:
        return "low"
    if avg_cost_for_two <= 2000:
        return "medium"
    return "high"


def _build_tags(row: dict[str, Any]) -> list[str]:
    tag_candidates = []
    for key in ("highlights", "establishment", "establishment_type"):
        if key in row and row[key] is not None:
            tag_candidates.append(row[key])
    joined = ",".join(str(item) for item in tag_candidates)
    return _normalize_cuisines(joined)


def _stable_id(name: str, city: str, area: str | None) -> str:
    base = f"{name}|{city}|{area or ''}".lower()
    safe = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return safe[:80]
