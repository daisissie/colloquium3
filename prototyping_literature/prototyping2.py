 #!/usr/bin/env python3
"""
This script:
  1. Extracts text from a Chinese EPUB file.
  2. Uses LAC (Lexical Analysis of Chinese) to extract location names directly from the Chinese text.
  3. Geocodes the extracted location names into latitude/longitude coordinates.
  4. Creates an interactive map (using Folium) with markers and a polyline connecting them.

Required packages:
    pip install ebooklib beautifulsoup4 LAC geopy folium
"""

import sys
import time
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from LAC import LAC
from geopy.geocoders import Nominatim
import folium

def extract_epub_text(file_path):
    """
    Extracts and concatenates text from all document items in the EPUB.
    """
    book = epub.read_epub(file_path)
    full_text = ""
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Remove HTML tags to get clean text.
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text(separator=" ", strip=True)
            full_text += text + "\n"
    return full_text

def extract_locations_chinese(text):
    """
    Uses LAC to perform Chinese NER and extract location names.
    Combines consecutive tokens tagged as 'LOC' into a single location entity.
    """
    lac = LAC(mode='lac')
    words, tags = lac.run(text)
    
    locations = []
    current_location = ""
    # Combine consecutive tokens tagged as "LOC"
    for word, tag in zip(words, tags):
        if tag == "LOC":
            current_location += word
        else:
            if current_location:
                locations.append(current_location)
                current_location = ""
    if current_location:
        locations.append(current_location)
    
    return locations

def geocode_locations(locations):
    """
    Geocodes location names into latitude and longitude using Nominatim.
    Returns a list of tuples: (location name, latitude, longitude).
    """
    geolocator = Nominatim(user_agent="chinese_location_mapper")
    loc_coords = []
    for loc in locations:
        try:
            geo = geolocator.geocode(loc)
            if geo:
                loc_coords.append((loc, geo.latitude, geo.longitude))
                print(f"Geocoded: {loc} -> ({geo.latitude}, {geo.longitude})")
            else:
                print(f"Location not found: {loc}")
            time.sleep(1)  # Respect Nominatim's usage policy.
        except Exception as e:
            print("Error geocoding", loc, e)
    return loc_coords

def create_map(loc_coords):
    """
    Creates a Folium map with markers for each location and a polyline connecting them.
    """
    if not loc_coords:
        return None

    # Center the map using the average of all coordinates.
    avg_lat = sum(lat for _, lat, lon in loc_coords) / len(loc_coords)
    avg_lon = sum(lon for _, lat, lon in loc_coords) / len(loc_coords)
    my_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=5)

    # Add markers.
    for loc, lat, lon in loc_coords:
        folium.Marker([lat, lon], popup=loc).add_to(my_map)

    # Draw a polyline connecting the locations.
    polyline_points = [(lat, lon) for _, lat, lon in loc_coords]
    folium.PolyLine(locations=polyline_points, color="blue", weight=2.5, opacity=1).add_to(my_map)
    return my_map

def main(epub_path):
    print("Extracting text from EPUB...")
    text = extract_epub_text(epub_path)
    
    print("Extracting location entities from Chinese text using LAC...")
    locations = extract_locations_chinese(text)
    
    # Remove duplicates while preserving order.
    unique_locations = []
    for loc in locations:
        if loc not in unique_locations:
            unique_locations.append(loc)
    print("Unique locations found:", unique_locations)
    
    print("Geocoding locations...")
    loc_coords = geocode_locations(unique_locations)
    
    print("Creating map...")
    my_map = create_map(loc_coords)
    if my_map:
        output_file = "map.html"
        my_map.save(output_file)
        print("Map saved to", output_file)
    else:
        print("No locations to map.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py path_to_epub_file")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    main(epub_file)