import spacy
from geopy.geocoders import Nominatim
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import csv
import json
import folium

# Load the spaCy model for English
nlp = spacy.load("en_core_web_sm")

file_path = '/Users/daiyu/Documents/github_mac/colloquium3/prototyping_literature/data/henry-david-thoreau_walden.epub'

def extract_text_from_epub(file_path):
    book = epub.read_epub(file_path)
    text = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            text.append(soup.get_text())

    return '\n'.join(text)

extracted_text = extract_text_from_epub(file_path)
doc = nlp(extracted_text)

# Extract location entities (GPE: Geopolitical Entities)
locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]

# Set up a geocoder (using OpenStreetMap's Nominatim service)
geolocator = Nominatim(user_agent="geo_extractor")

# Function to check if a location is a city
def is_city(location):
    loc = geolocator.geocode(location)
    if loc and 'city' in loc.raw['class']:
        return True
    return False

# Remove duplicate locations
unique_locations = list(set(locations))

# Open a CSV file for writing the location data
output_file = "locations.csv"
with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    # Write header row
    csvwriter.writerow(["Location", "Latitude", "Longitude"])
    
    geojson_features = []
    for location in unique_locations:
        if is_city(location):
            loc = geolocator.geocode(location)
            if loc:
                csvwriter.writerow([location, loc.latitude, loc.longitude])
                print(f"{location}: ({loc.latitude}, {loc.longitude})")
                geojson_features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [loc.longitude, loc.latitude]
                    },
                    "properties": {
                        "name": location
                    }
                })
            else:
                csvwriter.writerow([location, None, None])
                print(f"{location}: Geolocation not found")

# Write GeoJSON file
geojson_data = {
    "type": "FeatureCollection",
    "features": geojson_features
}
with open("locations.geojson", "w") as geojson_file:
    json.dump(geojson_data, geojson_file)

# Create a map
map = folium.Map(location=[0, 0], zoom_start=2)
for feature in geojson_features:
    folium.Marker(
        location=[feature["geometry"]["coordinates"][1], feature["geometry"]["coordinates"][0]],
        popup=feature["properties"]["name"]
    ).add_to(map)

# Save the map to an HTML file
map.save("locations_map.html")