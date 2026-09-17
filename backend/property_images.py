# backend/property_images.py
#
# Looks up listing photos for a property_id from data/property_images.csv.
# This is a plain local file read - no MCP, no network call - since photo
# URLs are static reference data, same spirit as create_database.py loading
# properties.csv into SQLite.
#
# CSV columns: property_id, image_1, image_2, image_3
# (see the "Property Images" note this was built from: URLs are stored,
# not downloaded, so a broker's real photos can replace these later by
# just swapping the CSV.)

import csv
from pathlib import Path

IMAGES_CSV_PATH = Path(__file__).resolve().parent / "data" / "property_images.csv"

_images_by_property_id: dict[str, list[str]] | None = None


def _load_images() -> dict[str, list[str]]:
    global _images_by_property_id

    if _images_by_property_id is not None:
        return _images_by_property_id

    images_by_property_id: dict[str, list[str]] = {}

    if IMAGES_CSV_PATH.exists():
        with open(IMAGES_CSV_PATH, newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                property_id = (row.get("property_id") or "").strip()

                if not property_id:
                    continue

                urls = [
                    row[column].strip()
                    for column in ("image_1", "image_2", "image_3")
                    if row.get(column, "").strip()
                ]

                images_by_property_id[property_id] = urls

    _images_by_property_id = images_by_property_id

    return _images_by_property_id


def get_property_images(property_id: str) -> list[str]:
    """Return this property's image URLs (main image first), or [] if none exist."""

    return _load_images().get(property_id, [])


def attach_images(property_dict: dict) -> dict:
    """Add an 'images' key to a property dict in place, then return it."""

    if not property_dict:
        return property_dict

    property_id = property_dict.get("property_id") or property_dict.get("id")
    property_dict["images"] = get_property_images(property_id) if property_id else []

    return property_dict
