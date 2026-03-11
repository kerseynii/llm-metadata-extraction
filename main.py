"""
Main entry point for the application.

This application:
1. Fetches building data from OpenStreetMap
2. Uses the LLM to extract structured information for the 10 most informative buildings
3. Exports the LLM-enriched results to GeoJSON
"""

import json
from dotenv import load_dotenv

from helpers import format_coordinates, get_env_variable
from llm_client import LLMClient
from osm_data_fetcher import OSMDataFetcher


# -------------------------------------------------------------
# Pretty print helpers
# -------------------------------------------------------------
def print_header(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def print_section(title):
    print(f"\n[{title}]")
    print("-" * 72)


# -------------------------------------------------------------
# Safe fallback for missing values
# -------------------------------------------------------------
def safe_value(value):
    if value is None:
        return "Information not found"

    value = str(value).strip()
    if value == "":
        return "Information not found"

    return value


# -------------------------------------------------------------
# Clean LLM JSON response
# -------------------------------------------------------------
def clean_llm_json(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # keep only the outermost JSON object if extra text exists
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text


# -------------------------------------------------------------
# Build raw building payload for the LLM
# -------------------------------------------------------------
def get_building_payload(building):
    lat = getattr(building, "lat", None)
    lon = getattr(building, "lon", None)

    return {
        "id": safe_value(getattr(building, "id", None)),
        "coordinates": (
            format_coordinates(lat, lon)
            if lat is not None and lon is not None
            else "Information not found"
        ),
        "raw_tags": {k: str(v) for k, v in building.tags.items()}
    }


# -------------------------------------------------------------
# Score buildings by metadata richness
# -------------------------------------------------------------
def score_building_information(building):
    useful_keys = [
        "name",
        "addr:street",
        "addr:housenumber",
        "addr:postcode",
        "addr:city",
        "height",
        "building:height",
        "est_height",
        "building:levels",
        "levels",
        "roof:shape",
        "roof:type",
        "start_date",
        "building:year",
        "year_built",
        "building",
        "amenity",
        "shop",
        "office",
        "tourism",
        "operator",
        "website",
        "wikidata",
        "heritage",
        "architect",
        "building:material",
    ]

    return sum(1 for key in useful_keys if key in building.tags)


# -------------------------------------------------------------
# Ask LLM to extract structured building metadata
# -------------------------------------------------------------
def extract_building_metadata_with_llm(llm_client, building_number, payload):
    system_prompt = """
You are a strict GIS building metadata extractor.

You will receive ONE building with raw OSM tags.

Rules:
- Use only the information explicitly present in the provided input
- Do NOT guess
- Do NOT infer from incomplete evidence
- Do NOT hallucinate
- If information is missing, return exactly: "Information not found"
- "building_use" means what the building is used for, not whether it is functioning
- Only fill "building_use" from explicit tags such as:
  building, amenity, shop, office, tourism, craft, leisure, religion, healthcare, public_transport
- Return ONLY valid JSON
- Do not add markdown fences
- Preserve original values exactly where possible

Return JSON with this structure:

{
  "building_number": <number>,
  "id": "...",
  "name": "...",
  "address": "...",
  "building_use": "...",
  "height": "...",
  "number_of_storeys": "...",
  "roof_type": "...",
  "construction_date": "...",
  "coordinates": "...",
  "additional_information": {}
}
"""

    user_prompt = f"""
Building number: {building_number}

Input building data:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = llm_client.chat(messages)
    cleaned = clean_llm_json(response)
    data = json.loads(cleaned)

    # ensure all expected fields exist
    required_fields = [
        "building_number",
        "id",
        "name",
        "address",
        "building_use",
        "height",
        "number_of_storeys",
        "roof_type",
        "construction_date",
        "coordinates",
        "additional_information",
    ]

    for field in required_fields:
        if field not in data:
            if field == "building_number":
                data[field] = building_number
            elif field == "additional_information":
                data[field] = {}
            else:
                data[field] = "Information not found"

    if not isinstance(data["additional_information"], dict):
        data["additional_information"] = {}

    return data


# -------------------------------------------------------------
# Export enriched building information to GeoJSON
# -------------------------------------------------------------
def export_enriched_buildings_geojson(enriched_items, output_path="enriched_buildings_llm.geojson"):
    features = []

    for item in enriched_items:
        lat = item["lat"]
        lon = item["lon"]

        if lat is None or lon is None:
            continue

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)]
            },
            "properties": item["metadata"]
        }

        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Exported {len(features)} enriched buildings → {output_path}")


# -------------------------------------------------------------
# MAIN APPLICATION
# -------------------------------------------------------------
def main():
    load_dotenv()

    ollama_base_url = get_env_variable("OLLAMA_BASE_URL")
    ollama_model = get_env_variable("OLLAMA_MODEL")
    overpass_api_url = get_env_variable("OVERPASS_API_URL", None)

    # Suggested richer OSM area: central Berlin (Mitte)
    bbox = (52.5160, 13.3970, 52.5245, 13.4120)

    print_header("LLM-Driven Building Metadata Extraction")

    llm_client = LLMClient(base_url=ollama_base_url, model=ollama_model)
    osm_fetcher = OSMDataFetcher(api_url=overpass_api_url)

    # -------------------------------------------------------------
    # 1 Fetch buildings from OSM
    # -------------------------------------------------------------
    print_section("1 OSM BUILDING FETCH")

    print(f"Bounding box: {bbox}")

    try:
        buildings = osm_fetcher.get_buildings_in_area(bbox)
        print(f"Buildings retrieved: {len(buildings)}")
    except Exception as e:
        print(f"OSM fetch error: {e}")
        buildings = []

    if not buildings:
        print("No buildings found in the bounding box.")
        return

    # -------------------------------------------------------------
    # 2 Select 10 buildings with the most metadata
    # -------------------------------------------------------------
    print_section("2 SELECT 10 MOST INFORMATIVE BUILDINGS")

    ranked_buildings = sorted(
        buildings,
        key=score_building_information,
        reverse=True
    )

    selected_buildings = ranked_buildings[:10]

    print(f"Selected buildings: {len(selected_buildings)}")

    # -------------------------------------------------------------
    # 3 LLM extraction
    # -------------------------------------------------------------
    print_section("3 LLM EXTRACTION FOR 10 BUILDINGS")

    enriched_items = []

    for i, building in enumerate(selected_buildings, 1):
        payload = get_building_payload(building)

        lat = getattr(building, "lat", None)
        lon = getattr(building, "lon", None)

        try:
            metadata = extract_building_metadata_with_llm(
                llm_client=llm_client,
                building_number=i,
                payload=payload
            )

            enriched_items.append({
                "lat": lat,
                "lon": lon,
                "metadata": metadata
            })

            print(f"\nBuilding {i}")
            print("-" * 72)
            print(f"Name               : {metadata['name']}")
            print(f"Address            : {metadata['address']}")
            print(f"Building Use       : {metadata['building_use']}")
            print(f"Height             : {metadata['height']}")
            print(f"Number of Storeys  : {metadata['number_of_storeys']}")
            print(f"Roof Type          : {metadata['roof_type']}")
            print(f"Construction Date  : {metadata['construction_date']}")
            print(f"Coordinates        : {metadata['coordinates']}")

            if metadata["additional_information"]:
                print("Additional Info    :")
                for key, value in metadata["additional_information"].items():
                    print(f"  - {key}: {value}")
            else:
                print("Additional Info    : Information not found")

        except Exception as e:
            print(f"\nBuilding {i}")
            print("-" * 72)
            print(f"LLM error: {e}")

    # -------------------------------------------------------------
    # 4 Export enriched metadata to GeoJSON
    # -------------------------------------------------------------
    print_section("4 EXPORT ENRICHED GEOJSON")
    export_enriched_buildings_geojson(enriched_items)

    print_header("Application Completed")


if __name__ == "__main__":
    main()