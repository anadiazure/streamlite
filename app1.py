import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import re
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLE_API_KEY = "AIzaSyByqkzi4Ga61VFZypik_F1Oikj7I8TVD28"

def get_anti_bot_token():
    """Retrieve anti-bot token from website."""
    url = "https://irisgst.com/irisperidot/"
    response = requests.get(url)
    
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    
    token_input = soup.find("input", {"name": "anti_bot_token"})
    if token_input and token_input.has_attr("value"):
        return token_input["value"]

    # Search token in scripts
    for script in soup.find_all("script"):
        if script.string:
            match = re.search(r"anti_bot_token\s*[:=]\s*['\"]([^'\"]+)['\"]", script.string)
            if match:
                return match.group(1)

    return None

def get_pin_code(gstn_number):
    """Scrape GSTIN filing detail page to get PIN code."""
    anti_bot_token = get_anti_bot_token()
    if not anti_bot_token:
        return None
    
    url = f"https://irisgst.com/irisperidot/gstin-filing-detail?gstinno={gstn_number}&anti_bot_token={anti_bot_token}"
    response = requests.get(url, timeout=10)
    
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    def p_with_principal_place(tag):
        return tag.name == "p" and tag.find("strong") and "Principal Place of Business -" in tag.get_text()

    p_tag = soup.find(p_with_principal_place)
    if p_tag:
        match = re.search(r'(\d{6})$', p_tag.get_text(strip=True))
        return match.group(1) if match else None

    return None

def get_coordinates(pin_code):
    """Fetch latitude & longitude for given PIN code."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={pin_code},India&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") == "OK":
        coords = data["results"][0]["geometry"]["location"]
        return coords["lat"], coords["lng"]
    return None

def get_geographical_distance(pin1, pin2):
    """Calculate driving distance between two PIN codes using Google Maps API."""
    coords1 = get_coordinates(pin1)
    coords2 = get_coordinates(pin2)

    if not coords1 or not coords2:
        return "Error retrieving distance"

    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={coords1[0]},{coords1[1]}&destinations={coords2[0]},{coords2[1]}&mode=driving&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") == "OK":
        return data["rows"][0]["elements"][0]["distance"]["text"]
    
    return "Error retrieving distance"

# Streamlit UI
st.title("GSTN Geographical Distance Calculator")

uploaded_file = st.file_uploader("Upload CSV file with GSTN1 and GSTN2 columns", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    if "GSTN1" in df.columns and "GSTN2" in df.columns:
        results = []

        # Fetch PIN codes for each GSTN pair in parallel
        with ThreadPoolExecutor() as executor:
            futures = {gstn: executor.submit(get_pin_code, gstn) for gstn in pd.concat([df["GSTN1"], df["GSTN2"]]).unique()}
            pin_codes = {gstn: future.result() for gstn, future in futures.items()}

        for _, row in df.iterrows():
            pin_code1 = pin_codes.get(row["GSTN1"])
            pin_code2 = pin_codes.get(row["GSTN2"])

            distance_km = get_geographical_distance(pin_code1, pin_code2) if pin_code1 and pin_code2 else "Error retrieving data"
            results.append({"GSTN1": row["GSTN1"], "GSTN2": row["GSTN2"], "Distance (km)": distance_km})

        result_df = pd.DataFrame(results)
        st.write(result_df)
    else:
        st.error("CSV file must contain GSTN1 and GSTN2 columns.")

# Direct user input method
gstn1 = st.text_input("Enter First GSTN Number")
gstn2 = st.text_input("Enter Second GSTN Number")
a
if st.button("Calculate Distance"):
    if gstn1 and gstn2:
        with ThreadPoolExecutor() as executor:
            future1 = executor.submit(get_pin_code, gstn1)
            future2 = executor.submit(get_pin_code, gstn2)
            pin_code1 = future1.result()
            pin_code2 = future2.result()

        distance_km = get_geographical_distance(pin_code1, pin_code2) if pin_code1 and pin_code2 else "Error retrieving data"
        st.success(f"Driving distance: {distance_km}")
    else:
        st.warning("Please enter both GSTN numbers.")
