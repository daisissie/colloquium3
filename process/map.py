import csv
import folium

# Read the CSV file
locations = []
with open("/Users/daiyu/Documents/github_mac/colloquium3/process/walden_locations.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if row["Latitude"] and row["Longitude"]:
            try:
                lat = float(row["Latitude"])
                lon = float(row["Longitude"])
                locations.append({"name": row["Location"], "lat": lat, "lon": lon})
            except ValueError:
                # Skip rows with invalid coordinates
                continue

# Determine a starting location for the map (e.g., average coordinates)
if locations:
    avg_lat = sum(loc["lat"] for loc in locations) / len(locations)
    avg_lon = sum(loc["lon"] for loc in locations) / len(locations)
    start_coords = [avg_lat, avg_lon]
else:
    # Fallback to a default location if no coordinates are available
    start_coords = [0, 0]

# Create a folium map centered at the starting coordinates
m = folium.Map(location=start_coords, zoom_start=5)

# Add markers for each location
for loc in locations:
    folium.Marker(
        location=[loc["lat"], loc["lon"]],
        popup=loc["name"]
    ).add_to(m)

# Save the map as an HTML file
m.save("map.html")
print("Map has been saved as map.html")