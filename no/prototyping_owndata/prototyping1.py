import os
import subprocess
import json
import folium
from decimal import Decimal

# Define your image folder path
folder_path = "/Users/daiyu/Documents/github_mac/colloquium3/prototyping_owndata/data/Photos-0209"

def extract_gps_from_jpeg(image_path):
    """Extract high-precision GPS coordinates from a JPEG image using ExifTool."""
    try:
        result = subprocess.run(
            ["exiftool", "-n", "-GPSLatitude", "-GPSLongitude", image_path],
            capture_output=True, text=True
        )
        output = result.stdout.strip().split("\n")

        lat = lon = None
        for line in output:
            if "GPS Latitude" in line:
                lat = line.split(":")[-1].strip()
            elif "GPS Longitude" in line:
                lon = line.split(":")[-1].strip()

        if lat and lon:
            return Decimal(lat), Decimal(lon)  # Use Decimal for precision
    except Exception as e:
        print(f"Error extracting GPS data from {image_path}: {e}")

    return None, None

def process_folder(folder_path):
    """Extract GPS data from all JPEG images in the folder."""
    features = []
    coordinates = []  # For centering the map

    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".jpeg", ".jpg")):
            image_path = os.path.join(folder_path, filename)
            lat, lon = extract_gps_from_jpeg(image_path)

            if lat and lon:
                coordinates.append([float(lat), float(lon)])
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)]  # GeoJSON format: [lon, lat]
                    },
                    "properties": {
                        "Image": filename,
                        "Latitude": round(float(lat), 6),
                        "Longitude": round(float(lon), 6)
                    }
                }
                features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }, coordinates

# Process folder and create GeoJSON data
geojson_data, coordinates = process_folder(folder_path)

# Save as GeoJSON file
geojson_path = "photo_locations.geojson"
with open(geojson_path, "w") as geojson_file:
    json.dump(geojson_data, geojson_file, indent=4)

print(f"✅ High-precision GPS data saved as GeoJSON: {geojson_path}")

# Create an interactive world map with Folium
if coordinates:
    avg_lat = sum([coord[0] for coord in coordinates]) / len(coordinates)
    avg_lon = sum([coord[1] for coord in coordinates]) / len(coordinates)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=2)

    # Add markers for each photo
    for feature in geojson_data["features"]:
        lat = feature["geometry"]["coordinates"][1]
        lon = feature["geometry"]["coordinates"][0]
        image_name = feature["properties"]["Image"]
        folium.Marker(
            location=[lat, lon],
            popup=image_name,
            icon=folium.Icon(color="blue", icon="camera")
        ).add_to(m)

    # Add GeoJSON overlay on the map
    folium.GeoJson(geojson_data, name="Photo Locations").add_to(m)

    # Save the map
    map_path = "photo_map.html"
    m.save(map_path)
    print(f"🌍 Interactive map saved as HTML: {map_path}")
else:
    print("❌ No valid GPS data found.")