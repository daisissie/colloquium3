import csv
import json
import sys
import os  # added

def csv_to_geojson(csv_file, geojson_file):
    features = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row['Latitude']) if row['Latitude'] else None
                lon = float(row['Longitude']) if row['Longitude'] else None
            except ValueError:
                lat = None
                lon = None
            if lat is None or lon is None:
                continue  # Skip rows with invalid coordinates
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "name": row.get("Location", ""),
                    "context": row.get("Context", "")
                }
            }
            features.append(feature)
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    with open(geojson_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=4)
    print(f"GeoJSON saved to {geojson_file}")

if __name__ == '__main__':
    input_folder = '/Users/daiyu/Documents/github_mac/colloquium3/csv_output'  # new constant
    csv_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.csv')]
    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        sys.exit(1)
    
    output_folder = '/Users/daiyu/Documents/github_mac/colloquium3/geojson_output'
    os.makedirs(output_folder, exist_ok=True)
    
    # Process all CSV files in the input folder
    for csv_file in csv_files:
        input_csv = os.path.join(input_folder, csv_file)
        base_name = os.path.splitext(os.path.basename(input_csv))[0]
        output_file = os.path.join(output_folder, f"{base_name}.geojson")
        print(f"Processing CSV: {input_csv}")
        csv_to_geojson(input_csv, output_file)
