import spacy
from geopy.geocoders import Nominatim
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import csv
import time
import os
import sys
import difflib

# ---------------------------
# 1. Text Extraction Functions (EPUB Only)
# ---------------------------

def extract_text(file_path):
    """
    Extracts text from an EPUB file.
    """
    if file_path.lower().endswith('.epub'):
        return extract_text_from_epub(file_path)
    else:
        raise ValueError("Unsupported file format. Please provide an .epub file.")

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

# Load the transformer-based spaCy model for English for improved NER.
# (Install via: python -m spacy download en_core_web_trf)
nlp = spacy.load("en_core_web_trf")

# Set up the geocoder using OpenStreetMap's Nominatim service.
geolocator = Nominatim(user_agent="geo_extractor")

def get_geocode(location, retries=3, timeout=10):
    """
    Returns the geocode result for a given location string.
    Tries multiple times with a specified timeout.
    """
    for attempt in range(retries):
        try:
            loc = geolocator.geocode(location, timeout=timeout)
            time.sleep(1)  # Pause to avoid rate limits
            if loc:
                return loc
        except Exception as e:
            print(f"Error geocoding {location} (attempt {attempt+1}): {e}")
    return None

def is_city(loc):
    """
    Checks if the geocoded location is acceptable.
    Excludes locations classified as a country.
    Accepts types: city, town, village, hamlet, locality.
    """
    if loc:
        loc_type = loc.raw.get('type', '')
        if loc_type == 'country':
            return False
        if loc_type in ['city', 'town', 'village', 'hamlet', 'locality']:
            return True
        # Accept other types if needed.
        return True
    return False

def is_in_united_states(loc):
    """
    Checks if the geocoded location is in the United States.
    """
    if loc and loc.raw.get("address"):
        address = loc.raw["address"]
        return address.get("country_code", "").lower() == "us"
    return False

def get_context(doc, start_char, end_char):
    """
    Retrieves the full sentence containing the target text from the spaCy document.
    If no sentence fully contains the target, a fallback window is returned.
    """
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

def process_file(file_path):
    extracted_text = extract_text(file_path)
    doc = nlp(extracted_text)
    
    # Extract locations using NER from spaCy.
    locations_info = []
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            locations_info.append((ent.text, ent.start_char, ent.end_char))
    
    # Combine repeated locations and store all their context occurrences.
    unique_locations = {}
    for loc_text, start_char, end_char in locations_info:
        normalized = loc_text.lower().strip()
        found_key = None
        for key in unique_locations.keys():
            if difflib.SequenceMatcher(None, normalized, key).ratio() > 0.8:
                found_key = key
                break
        if found_key is not None:
            unique_locations[found_key]["occurrences"].append((start_char, end_char))
        else:
            unique_locations[normalized] = {"orig_text": loc_text, "occurrences": [(start_char, end_char)]}
    
    # Prepare output CSV file.
    output_dir = "/Users/daiyu/Documents/github_mac/colloquium3/csv_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_csv_file = os.path.join(output_dir, f"locations_{base_name}.csv")
    
    with open(output_csv_file, mode='w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Location", "Latitude", "Longitude", "Context"])
        for norm_text, data in unique_locations.items():
            orig_text = data["orig_text"]
            occurrences = data["occurrences"]
            # Combine all contexts from repeated occurrences, separated by " | "
            context_list = [get_context(doc, start, end) for start, end in occurrences]
            combined_context = " | ".join(context_list)
            loc = get_geocode(orig_text)
            if loc and is_in_united_states(loc) and is_city(loc):
                csvwriter.writerow([orig_text, loc.latitude, loc.longitude, combined_context])
            else:
                csvwriter.writerow([orig_text, None, None, combined_context])
    return f"CSV file '{output_csv_file}' has been created."

def main():
    input_dir = "/Users/daiyu/Documents/github_mac/colloquium3/use_data"
    if not os.path.exists(input_dir):
        print(f"Input folder {input_dir} does not exist.")
        sys.exit(1)
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if os.path.isfile(file_path) and file_path.lower().endswith('.epub'):
            print(f"Processing file: {file_path}")
            result = process_file(file_path)
            print(result)

if __name__ == "__main__":
    main()