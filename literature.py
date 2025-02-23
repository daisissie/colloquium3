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
import subprocess
from striprtf.striprtf import rtf_to_text

# ---------------------------
# 1. Text Extraction Functions
# ---------------------------

def extract_text(file_path):
    """
    Extracts text from an EPUB, MOBI, TXT, or RTF file based on its extension.
    """
    if file_path.lower().endswith('.epub'):
        return extract_text_from_epub(file_path)
    elif file_path.lower().endswith('.mobi'):
        return extract_text_from_mobi(file_path)
    elif file_path.lower().endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif file_path.lower().endswith('.rtf'):
        return extract_text_from_rtf(file_path)
    else:
        raise ValueError("Unsupported file format. Please provide a .epub, .mobi, .txt, or .rtf file.")

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

def convert_mobi_to_epub(input_path, output_path):
    """
    Converts a MOBI file to EPUB format using the ebook-convert command.
    Ensure that Calibre's ebook-convert is installed and accessible from the PATH.
    """
    command = ['ebook-convert', input_path, output_path]
    subprocess.run(command, check=True)

def extract_text_from_mobi(file_path):
    """
    Extracts text content from a MOBI file by converting it to EPUB and then using extract_text_from_epub.
    """
    temp_epub = "temp_converted.epub"
    convert_mobi_to_epub(file_path, temp_epub)
    text = extract_text_from_epub(temp_epub)
    os.remove(temp_epub)  # Clean up the temporary EPUB file
    return text

def extract_text_from_rtf(file_path):
    """
    Reads an RTF file and extracts its text content.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        rtf_content = f.read()
    return rtf_to_text(rtf_content)

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
        time.sleep(1)  # Pause to avoid rate limits
        return loc
    except Exception as e:
        print(f"Error geocoding {location}: {e}")
        return None

def is_city(loc):
    """
    Checks if the geocoded location is of an acceptable type.
    Adjust this function if needed.
    """
    if loc:
        loc_type = loc.raw.get('type', '')
        if loc_type in ['city', 'town', 'village', 'hamlet', 'locality']:
            return True
        # For now, accept all geocoded results.
        return True
    return False

def get_context(doc, start_char, end_char):
    """
    Retrieves the full sentence containing the target text from the spaCy document.
    If no sentence fully contains the target, a fallback window is returned.
    """
    # Attempt to extract the complete sentence containing the given character range.
    for sent in doc.sents:
        if sent.start_char <= start_char and sent.end_char >= end_char:
            return sent.text.strip()
    
    # Fallback: Return a longer fixed window if no sentence boundary is found.
    context_start = max(0, start_char - 100)
    context_end = min(len(doc.text), end_char + 100)
    return doc.text[context_start:context_end].strip()

# ---------------------------
# 3. Main Workflow
# ---------------------------

# Specify your input file path (change as needed)
file_path = '/Users/daiyu/Documents/github_mac/colloquium3/prototying_tuvalu/data/Tuvalu1.rtf'
extracted_text = extract_text(file_path)

# Process the text using spaCy to extract entities
doc = nlp(extracted_text)

# Extract GPE (Geopolitical Entity) entities along with their character offsets
locations_info = []
for ent in doc.ents:
    if ent.label_ == "GPE":
        locations_info.append((ent.text, ent.start_char, ent.end_char))

# Remove duplicate locations while keeping the first occurrence for context extraction
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
        if loc and is_city(loc):
            context = get_context(doc, start_char, end_char)
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