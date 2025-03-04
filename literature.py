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
import nltk
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from nltk.sentiment import SentimentIntensityAnalyzer

# ---------------------------
# 1. Text Extraction Functions
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
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error geocoding {location} (attempt {attempt+1}): {e}")
            if attempt == retries - 1:
                return None  # Only return None after all retries have failed
        except Exception as e:
            print(f"Unexpected error geocoding {location}: {e}")
            return None
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

def get_context(doc, start_char, end_char):
    """
    Retrieves the full sentence containing the target text from the spaCy document.
    Returns the sentence as a spaCy Span object.
    """
    for sent in doc.sents:
        if sent.start_char <= start_char and sent.end_char >= end_char:
            return sent
    # Fallback: Return a longer fixed window if no sentence boundary is found.
    context_start = max(0, start_char - 100)
    context_end = min(len(doc.text), end_char + 100)
    return doc.text[context_start:context_end].strip()

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

def determine_presence(sentence, location):
    """
    Determines whether the author was physically present at the location.
    """
    # Analyze sentiment
    sentiment_score = sia.polarity_scores(sentence)["compound"]

    # Check for keywords
    physical_keywords = ["visited", "saw", "walked", "lived", "stayed"]
    mental_keywords = ["thought", "imagined", "remembered", "dreamed"]

    physical_presence = any(keyword in sentence.lower() for keyword in physical_keywords)
    mental_presence = any(keyword in sentence.lower() for keyword in mental_keywords)

    # Analyze dependency parsing
    doc = nlp(sentence)
    for token in doc:
        if token.dep_ == "ROOT" and token.lemma_ in ["visit", "see", "walk", "live", "stay"]:
            physical_presence = True
        if token.dep_ == "ROOT" and token.lemma_ in ["think", "imagine", "remember", "dream"]:
            mental_presence = True

    # Make a determination based on the analysis
    if physical_presence and not mental_presence:
        return "Physically present"
    elif mental_presence and not physical_presence:
        return "Mentally present"
    elif physical_presence and mental_presence:
        return "Both physically and mentally present"
    else:
        if sentiment_score > 0.5:
            return "Likely physically present (positive sentiment)"
        else:
            return "Unclear"

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
    
    # Prepare output CSV file.
    output_dir = "/Users/daiyu/Documents/github_mac/colloquium3/csv_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_csv_file = os.path.join(output_dir, f"locations_{base_name}.csv")
    
    with open(output_csv_file, mode='w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Location", "Latitude", "Longitude", "Context", "Presence"])
        
        # Iterate through the locations in the order they appear
        for loc_text, start_char, end_char in locations_info:
            context = get_context(doc, start_char, end_char)
            if isinstance(context, spacy.tokens.Span):
                presence = determine_presence(context.text, loc_text)
                loc = get_geocode(loc_text)
                if loc and is_city(loc):
                    csvwriter.writerow([loc_text, loc.latitude, loc.longitude, context.text, presence])
                    print(f"Geocoded {loc_text}: ({loc.latitude}, {loc.longitude}), Presence: {presence}")
                else:
                    csvwriter.writerow([loc_text, None, None, context.text, presence])
                    print(f"Could not geocode or did not meet criteria: {loc_text}, Presence: {presence}")
            else:
                csvwriter.writerow([loc_text, None, None, context, "Unclear"])
                print(f"Could not determine presence: {loc_text}")
                
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