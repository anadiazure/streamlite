import streamlit as st
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import re

# Google Maps API Key (Replace with your actual key)
GOOGLE_API_KEY = "AIzaSyDo4A0wra-QnxHYmHzWmbXPuiJ8xceBdeA"

def get_pin_code(gstn_number):
    """Fetches the PIN code from the GSTN details API."""
    url = f"https://irisgst.com/gstin-filing-detail/?gstinno={gstn_number}&anti_bot_token=MTc0NzY3MzUxNToyMTk0MDZhMDBiNzM0NTAyNzI3Y2ZkOTYxMDc1NGVkMWYwZjQxMGUxNDIwMTQyYmYzMjNiODY3MzdmNTljNmJi"

    response = requests.get(url)

    if response.status_code != 200:
        return None  # Ensure successful response
    
    # Extract text content from the response
    text_data = response.text
    print(text_data)

    # Use regex to extract the 6-digit PIN code from the response
    pin_code_match = re.search(r'\b\d{6}\b', text_data)

    return pin_code_match.group(0) if pin_code_match else None

    # Extract the target element containing PIN code
    element = soup.find("p", string=lambda text: text and "Principal Place of Business -" in text)
    if element:
        text_data = element.get_text(strip=True)
        pin_code_match = re.search(r'\b\d{6}\b', text_data)
        return pin_code_match.group(0) if pin_code_match else None
    
    return None

def get_coordinates(pin_code):
    """Fetch latitude & longitude for a given PIN code using Google Maps API."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={pin_code},India&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if data["status"] == "OK":
        coords = data["results"][0]["geometry"]["location"]
        return coords["lat"], coords["lng"]
    return None

def get_geographical_distance(pin1, pin2):
    """Uses Google Maps API to get driving distance between two PIN codes."""
    coords1 = get_coordinates(pin1)
    coords2 = get_coordinates(pin2)

    if coords1 and coords2:
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={coords1[0]},{coords1[1]}&destinations={coords2[0]},{coords2[1]}&mode=driving&key={GOOGLE_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if data["status"] == "OK":
            distance_text = data["rows"][0]["elements"][0]["distance"]["text"]
            return distance_text
    return None

# Streamlit UI
st.title("GSTN Geographical Distance Calculator (Google Maps)")

gstn1 = st.text_input("Enter First GSTN Number")
gstn2 = st.text_input("Enter Second GSTN Number")

if st.button("Calculate Distance"):
    if gstn1 and gstn2:
        # Fetch PIN codes in parallel
        with ThreadPoolExecutor() as executor:
            future1 = executor.submit(get_pin_code, gstn1)
            future2 = executor.submit(get_pin_code, gstn2)
            pin_code1 = future1.result()
            pin_code2 = future2.result()

        if pin_code1 and pin_code2:
            # Get actual driving distance using Google Maps API
            distance_km = get_geographical_distance(pin_code1, pin_code2)
            if distance_km:
                st.success(f"Driving distance between {pin_code1} and {pin_code2}: {distance_km}")
            else:
                st.error("Could not retrieve the geographical driving distance.")
        else:
            st.error("Could not retrieve PIN codes for one or both GSTNs.")
    else:
        st.warning("Please enter both GSTN numbers.")
