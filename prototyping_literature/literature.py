import spacy
from geopy.geocoders import Nominatim
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import csv
import json
import folium
import time
import os

# ---------------------------
# 1. Text Extraction Functions
# ---------------------------

def extract_text(file_path):
    """
    Extracts text from an EPUB or TXT file based on its extension.
    """
    if file_path.lower().endswith('.epub'):
        return extract_text_from_epub(file_path)
    elif file_path.lower().endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError("Unsupported file format. Please provide a .epub or .txt file.")

def extract_text_from_epub(file_path):
    """
    Reads an EPUB file and extracts its text content using BeautifulSoup.
    """
    book = epub.read_epub(file_path)
    text = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            text.append(soup.get_text())
    return '\n'.join(text)

# ---------------------------
# 2. Setup NLP and Geocoder
# ---------------------------

# Load the spaCy model for English
nlp = spacy.load("en_core_web_sm")

# Set up the geocoder using OpenStreetMap's Nominatim service
geolocator = Nominatim(user_agent="geo_extractor")

def get_geocode(location):
    """
    Returns the geocode result for a given location string.
    Includes a delay to respect rate limits.
    """
    try:
        loc = geolocator.geocode(location)
        time.sleep(1)  # pause to avoid rate limits
        return loc
    except Exception as e:
        print(f"Error geocoding {location}: {e}")
        return None

def is_city(loc):
    if loc:
        # Accept if type is one of a broader set, or simply return True if loc exists.
        loc_type = loc.raw.get('type', '')
        if loc_type in ['city', 'town', 'village', 'hamlet', 'locality']:
            return True
        # Or remove the check altogether:
        return True
    return False

def get_context(text, start_char, end_char, window=50):
    """
    Retrieves a snippet of text surrounding the location occurrence.
    """
    context_start = max(0, start_char - window)
    context_end = min(len(text), end_char + window)
    return text[context_start:context_end]

# ---------------------------
# 3. Main Workflow
# ---------------------------

# Specify your input file path (change as needed)
file_path = '/Users/daiyu/Documents/github_mac/colloquium3/prototyping_literature/data/henry-david-thoreau_walden.epub'
extracted_text = extract_text(file_path)

# Process the text using spaCy
doc = nlp(extracted_text)

# Extract GPE entities along with their character offsets
locations_info = []
for ent in doc.ents:
    if ent.label_ == "GPE":
        locations_info.append((ent.text, ent.start_char, ent.end_char))

# Remove duplicates while keeping the first occurrence for context extraction
unique_locations = {}
for loc_text, start_char, end_char in locations_info:
    if loc_text not in unique_locations:
        unique_locations[loc_text] = (start_char, end_char)

# Prepare CSV and GeoJSON outputs
output_csv_file = "locations.csv"
geojson_features = []

with open(output_csv_file, mode='w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    # Write header row
    csvwriter.writerow(["Location", "Latitude", "Longitude", "Context"])
    
    for location, (start_char, end_char) in unique_locations.items():
        loc = get_geocode(location)
        # Check if geocoding was successful and if the result is a city-like entity
        if loc and is_city(loc):
            context = get_context(extracted_text, start_char, end_char)
            csvwriter.writerow([location, loc.latitude, loc.longitude, context])
            print(f"{location}: ({loc.latitude}, {loc.longitude})")
            geojson_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [loc.longitude, loc.latitude]
                },
                "properties": {
                    "name": location,
                    "context": context
                }
            })
        else:
            csvwriter.writerow([location, None, None, None])
            print(f"{location}: Geolocation not found or not considered a city.")

# Write GeoJSON file
geojson_data = {
    "type": "FeatureCollection",
    "features": geojson_features
}

with open("locations.geojson", "w", encoding='utf-8') as geojson_file:
    json.dump(geojson_data, geojson_file)

# Create an interactive map using Folium
m = folium.Map(location=[0, 0], zoom_start=2)
for feature in geojson_features:
    folium.Marker(
        location=[feature["geometry"]["coordinates"][1], feature["geometry"]["coordinates"][0]],
        popup=f"{feature['properties']['name']}: {feature['properties']['context']}"
    ).add_to(m)

# Save the map to an HTML file
m.save("locations_map.html")

print("Processing complete. CSV, GeoJSON, and map files have been created.")