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
import difflib
import sys

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

# Load the transformer-based spaCy model for English for improved NER.
# (Install via: python -m spacy download en_core_web_trf)
nlp = spacy.load("en_core_web_trf")

# Set up the geocoder using OpenStreetMap's Nominatim service.
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
        # Accept other types if needed (e.g., region, suburb, etc.)
        return True
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
    locations_info = []
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            locations_info.append((ent.text, ent.start_char, ent.end_char))
    unique_locations = {}
    for loc_text, start_char, end_char in locations_info:
        normalized = loc_text.lower().strip()
        similar_found = False
        for key in unique_locations.keys():
            if difflib.SequenceMatcher(None, normalized, key).ratio() > 0.8:
                similar_found = True
                break
        if not similar_found:
            unique_locations[normalized] = (loc_text, start_char, end_char)
    
    # Write output as CSV and store it in the new output folder
    output_dir = "/Users/daiyu/Documents/github_mac/colloquium3/csv_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_csv_file = os.path.join(output_dir, f"locations_{base_name}.csv")
    
    import csv
    with open(output_csv_file, mode='w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Location", "Latitude", "Longitude", "Context"])
        for norm_text, (orig_text, start_char, end_char) in unique_locations.items():
            loc = get_geocode(orig_text)
            if loc and is_city(loc):
                context = get_context(doc, start_char, end_char)
                csvwriter.writerow([orig_text, loc.latitude, loc.longitude, context])
            else:
                csvwriter.writerow([orig_text, None, None, None])
    return f"CSV file '{output_csv_file}' has been created."

def main():
    input_dir = "/Users/daiyu/Documents/github_mac/colloquium3/use_data"
    if not os.path.exists(input_dir):
        print(f"Input folder {input_dir} does not exist.")
        sys.exit(1)
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if os.path.isfile(file_path) and file_path.lower().endswith(('.epub', '.mobi', '.txt', '.rtf')):
            print(f"Processing file: {file_path}")
            result = process_file(file_path)
            print(result)

if __name__ == "__main__":
    main()