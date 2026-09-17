import os
import csv
import time
import requests
from dotenv import load_dotenv


load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
IMAGES_FILE = "data/property_images.csv"
PROPERTIES_FILE = "data/properties.csv"
OUTPUT_FILE = "data/property_images.csv"

PEXELS_URL = "https://api.pexels.com/v1/search"

# Pexels default limit: 200 requests/hour
# We use a much smaller batch for safety.
BATCH_SIZE = 50

# Pause between requests
REQUEST_DELAY = 1


def search_pexels(query):

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": query,
        "per_page": 1
        # We're asking for one result because we only need one photo for each category.
    }

    response = requests.get(
        PEXELS_URL,
        headers=headers,
        params=params,
        timeout=15
        # After 15 seconds, the request can fail instead of hanging your program indefinitely.
    )

    if response.status_code == 429:
        print("Pexels rate limit reached.")
        return None

    response.raise_for_status()

    data = response.json()

    if not data["photos"]:
        return ""

    return data["photos"][0]["src"]["large"]


def load_completed_properties():

    if not os.path.exists(OUTPUT_FILE):
        return set()

    completed = set()

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            completed.add(row["property_id"])

    return completed


def create_image_mapping():

    with open(
        PROPERTIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        properties = list(csv.DictReader(file))

    completed = load_completed_properties()

    remaining = [
        property
        for property in properties
        if property["property_id"] not in completed
    ]

    print(f"Total properties: {len(properties)}")
    print(f"Already completed: {len(completed)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("\nAll properties already have images.")
        return

    # Create file with header if it doesn't exist
    if not os.path.exists(OUTPUT_FILE):

        with open(
            OUTPUT_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "property_id",
                "image_1",
                "image_2",
                "image_3"
            ])

    # Process only one batch
    batch = remaining[:BATCH_SIZE]

    print(f"\nProcessing {len(batch)} properties in this batch.")

    with open(
        OUTPUT_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        for index, property in enumerate(batch, start=1):

            property_id = property["property_id"]
            property_type = property["property_type"]
            bhk = property["bhk"]

            print(
                f"\n[{index}/{len(batch)}] "
                f"Processing {property_id}"
            )

            # 1. Exterior
            query_1 = (
                f"modern luxury "
                f"{property_type} exterior"
            )

            # 2. Living room
            query_2 = (
                f"modern {bhk} bedroom "
                f"{property_type} living room"
            )

            # 3. Bedroom
            query_3 = (
                f"modern {bhk} bedroom "
                f"{property_type} bedroom interior"
            )

            try:

                print(f"  → Exterior")
                image_1 = search_pexels(query_1)

                time.sleep(REQUEST_DELAY)

                if image_1 is None:
                    print("Rate limit reached. Stopping batch.")
                    break

                print(f"  → Living room")
                image_2 = search_pexels(query_2)

                time.sleep(REQUEST_DELAY)

                if image_2 is None:
                    print("Rate limit reached. Stopping batch.")
                    break

                print(f"  → Bedroom")
                image_3 = search_pexels(query_3)

                if image_3 is None:
                    print("Rate limit reached. Stopping batch.")
                    break

                writer.writerow([
                    property_id,
                    image_1,
                    image_2,
                    image_3
                ])

                file.flush()

                print("  ✓ Saved")

                time.sleep(REQUEST_DELAY)

            except Exception as e:

                print(
                    f"  ✗ Error for {property_id}: {e}"
                )

                continue

    print("\n--------------------------------")
    print("Batch completed.")
    print(f"Processed: {len(batch)} properties")
    print("--------------------------------")
    
def get_property_images(property_id):
    with open(IMAGES_FILE, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["property_id"] == property_id:
                return [
                    row["image_1"],
                    row["image_2"],
                    row["image_3"]
                ]

    return []

if __name__ == "__main__":
    create_image_mapping()