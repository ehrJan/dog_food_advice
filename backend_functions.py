from PIL import Image
from pyzbar.pyzbar import decode
import requests # Library to send HTTP requests - asking web server for data
import json
import os
import google.generativeai as genai
import textwrap
import streamlit as st


def load_image(path_image):
    """Loads an image from the given file path."""

    return Image.open(path_image) 
def scan_barcode_from_image(path_image):
    image=load_image(path_image=path_image)
    
    decoded_objects = decode(image)

    try:
        if decoded_objects:
            print(f"{len(decoded_objects)} barcode(s) recognized:")
            return decoded_objects[0].data.decode("utf-8")
        else:
            print("❌ no barcode recocognized")
    except Exception as e:
        print(f"Barcode reading failed with {e}")
        return None
    

def strip_leading_zeros(barcode_str):
  """
  Removes leading zeros from a barcode string.

  Args:
    barcode_str: The input string representing the barcode.

  Returns:
    The barcode string with leading zeros removed.
    Returns '0' if the input consists only of zeros.
    Returns an empty string if the input is empty.
    Returns the original string if there are no leading zeros.
  """
  if not isinstance(barcode_str, str):
    # Optional: Handle non-string input, e.g., convert or raise error
    # For simplicity, we'll try converting, but a TypeError might be safer
    try:
        barcode_str = str(barcode_str)
    except Exception:
        raise TypeError("Input must be a string or convertible to a string.")

  stripped_barcode = barcode_str.lstrip('0')

  if barcode_str and not stripped_barcode and '0' in barcode_str:
    return '0'
  else:
    return stripped_barcode
  

def get_nutrition_data(barcode_to_find):
    stiped_barcode=strip_leading_zeros(barcode_str=str(barcode_to_find))
    api_url = f"https://world.openpetfoodfacts.org/api/v2/product/{stiped_barcode}?fields=product_name,brands,ingredients_text,ingredients_text,serving_size,energy-kcal_100g,fat_100g,carbohydrates_100g,proteins_100g" # Constructs API URL, defines datapoints we want
    try: # Sends an HTTP GET request to the URL we built
        response = requests.get(api_url, headers={'User-Agent': 'YourProjectName - Python - Version 1.0'}) # Identifing our app
        response.raise_for_status() # Raises an error for bad status codes (4xx or 5xx), if so this code will jump to except block
        data = response.json() # Parsing JSON response + convert to dictionary (if successful)
        if data.get('status') == 1 and 'product' in data: # Check if product was found (API returns status 1 if found)

            return data['product'] # If found, return the dictionary containing the product details

        else:
            return None # Product not found or error in response
        # Handling potential errors during the request below
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to parse API response")
        return None

class ai_agent:
    def __init__(self,path_env='keys.env'
                 ,base_prompt="Imagine you are a vetenarian specilised to work with dogs. You will be provided with dog race, age and weight. Furthermore will be provided with a specific type of dog food and its nutritions. Give me back a short and precise description on how much of the food the provided dog should eat and if it is generally good for him"
                 ,model_type="gemini-1.5-flash"):
        self.PATH_ENV=path_env
        self.base_prompt=base_prompt
        self.model_type=model_type

        genai.configure(api_key=self.get_gemini_api_key())

        self.model=genai.GenerativeModel(self.model_type)

    def get_gemini_api_key(self,key="gemini_api"):
        return st.secrets[key]

    def create_prompt_string(self,food_dict,dog_dict):
        content_generation_string=self.base_prompt
        content_generation_string+="The dog has the following properties:"
        content_generation_string+=str(dog_dict)

        content_generation_string+="The food has the following properties:"
        content_generation_string+=str(food_dict)

        return content_generation_string

    def create_response(self,food_dict,dog_dict):
        prompt=self.create_prompt_string(food_dict=food_dict,dog_dict=dog_dict)
        
        response = self.model.generate_content(prompt)

        return response.text

