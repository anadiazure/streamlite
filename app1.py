import streamlit as st
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import re

# Google Maps API Key (Replace with your actual key)
GOOGLE_API_KEY = "AIzaSyAXH8AuaroD8hnb47UEiIswJLQGcnZJRzs"

def get_anti_bot_token():
    url = "https://irisgst.com/irisperidot/"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve page. Status code: {response.status_code}")
        return None

    # Parse the page content with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Option 1: Check if the token is in an <input> element with name "anti_bot_token".
    token_input = soup.find("input", {"name": "anti_bot_token"})
    if token_input and token_input.has_attr("value"):
        return token_input["value"]

    # Option 2: Look inside <script> tags for a variable named "anti_bot_token".
    for script in soup.find_all("script"):
        # Ensure the script tag contains text.
        if script.string:
            # This regular expression looks for a pattern like:
            # anti_bot_token = "TOKEN_VALUE" or anti_bot_token: "TOKEN_VALUE"
            match = re.search(r"anti_bot_token\s*[:=]\s*['\"]([^'\"]+)['\"]", script.string)
            if match:
                return match.group(1)

    # Option 3: Fallback: search the whole HTML text using regex
    match = re.search(r"anti_bot_token\s*[:=]\s*['\"]([^'\"]+)['\"]", response.text)
    if match:
        return match.group(1)

    return None
def get_pin_code(gstn_number):
    """
    Scrapes the GSTIN filing detail page using BeautifulSoup.
    Focuses on debugging the element finding process.
    """
    base_url = "https://irisgst.com/gstin-filing-detail/"
    anti_bot_token = get_anti_bot_token()
    url = f"https://irisgst.com/irisperidot/gstin-filing-detail?gstinno={gstn_number}&anti_bot_token={anti_bot_token}"

    print(f"Attempting to fetch URL: {url}")

    try:
        response = requests.get(url, timeout=10)
        print(f"Response status code: {response.status_code}")

        if response.status_code != 200:
            print("Request failed with status code:", response.status_code)
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        print("HTML content successfully parsed by BeautifulSoup.")

        # >>> DEBUGGING STEP: Print the HTML received <<<
        # print("--- Start of Parsed HTML ---")
        # print(soup.prettify())
        # print("--- End of Parsed HTML ---")
        # >>> END DEBUGGING STEP <<<

        def p_with_principal_place(tag):
            if tag.name != 'p':
                # print(f"Skipping tag: <{tag.name}>") # Debug print if not <p>
                return False
            strong = tag.find('strong')
            # print(f"Found strong tag in <p>: {strong}") # Debug print finding strong
            if strong is not None:
                 # print(f"Strong tag text: '{strong.get_text()}'") # Debug print strong text
                 if "Principal Place of Business -" in strong.get_text():
                      # print("Found 'Principal Place of Business -' in strong text.") # Debug print found text
                      return True
            return False

        p_tag = soup.find(p_with_principal_place)

        print(f"Result of soup.find: {p_tag}") # This will tell you if the element was found

        if p_tag:
            text_data = p_tag.get_text(strip=True)
            print(f"Extracted text from element: '{text_data}'")
            match = re.search(r'(\d{6})$', text_data)
            print(f"Regex match result: {match}")

            if match:
                print(f"Successfully extracted PIN code: {match.group(1)}")
                return match.group(1)
            else:
                print("Regex did not find a 6-digit number at the end of the text.")
        else:
            print("Could not find the <p> element with 'Principal Place of Business -' using the filter.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return None

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
