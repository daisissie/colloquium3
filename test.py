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
from geopy.geocoders import Nominatim

def get_location_candidates(location_query):
    """
    Return all candidate locations for the given query.
    """
    geolocator = Nominatim(user_agent="geocode_app")
    return geolocator.geocode(location_query, exactly_one=False)

if __name__ == '__main__':
    query = input("Springfield")  # <-- this is where you input the location name
    candidates = get_location_candidates(query)
    if candidates:
        for candidate in candidates:
            print(candidate.address, "->", candidate.latitude, candidate.longitude)
    else:
        print("No location found.")
