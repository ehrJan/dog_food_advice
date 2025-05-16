import streamlit as st
import logging
import tempfile
import pandas as pd
import os

# --- Define the Correct Password ---
# For Streamlit Cloud, it will use st.secrets. For local, it falls back to os.getenv
# Ensure APP_PASSWORD is set in your Streamlit Cloud secrets or local .env file
CORRECT_PASSWORD = st.secrets["APP_PASSWORD"]

# --- Import your backend functions ---
try:
    from backend_functions import scan_barcode_from_image, get_nutrition_data, ai_agent
except ImportError as e:
    st.error(f"Error importing backend functions: {e}")
    st.error("Make sure 'backend_functions.py' is in the same directory as this script.")
    st.stop()

# --- Initialize AI Agent ---
try:
    ai_model = ai_agent()
except Exception as e:
    st.error(f"Error initializing AI Agent: {e}")
    st.error("Please ensure your API key is configured correctly.")
    st.stop()

# --- Logging Setup (remains the same) ---
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app_log.log")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
    ]
)

def log_interaction(barcode, dog_info, nutrition_data, recommendation):
    log_message = (
        f"Interaction Log:\n"
        f"\tBarcode: {barcode}\n"
        f"\tDog Info: {dog_info}\n"
        f"\tNutrition Data: {nutrition_data}\n"
        f"\tRecommendation: {recommendation.replace(os.linesep, ' ')}"
    )
    logging.info(log_message)

def process_image_input(image_file_like_object):
    barcode = None
    temp_image_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(image_file_like_object.getvalue())
            temp_image_path = tmp_file.name
        barcode = scan_barcode_from_image(temp_image_path)
        if not barcode:
            st.error("Could not detect a barcode in the image. Please try entering it manually.")
        else:
            st.success(f"Detected Barcode: {barcode}")
            return barcode
    except Exception as e:
        st.error(f"Error processing image: {e}")
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
    return None


st.set_page_config(page_title="Dog Food Analyzer AI", layout="wide")
st.title("🐾 Dog Food Analyzer & AI Recommender")
st.markdown("Scan a food barcode, take a photo, or enter it manually. Provide your dog's details for AI-powered feeding recommendations.")

input_col, output_col = st.columns(2)

with input_col:
    st.header("1. Food Barcode")
    barcode_source = st.radio(
        "Select Barcode Source:",
        ('Upload Image', 'Enter Manually', 'Take Photo (Webcam)'),
        key='barcode_source_radio',
        horizontal=True
    )
    uploaded_file = None
    manual_barcode = ""
    camera_photo = None
    if barcode_source == 'Upload Image':
        uploaded_file = st.file_uploader("Upload an image of the barcode:", type=["png", "jpg", "jpeg"], key='barcode_uploader')
    elif barcode_source == 'Take Photo (Webcam)':
        camera_photo = st.camera_input("Point camera at barcode and take photo:", key='barcode_camera')
    else:
        manual_barcode = st.text_input("Enter Barcode Number:", key='manual_barcode_input', placeholder="e.g., 0001234567890")

    st.divider()
    st.header("2. Your Dog's Details")
    dog_breed = st.text_input("Breed:", key='dog_breed', placeholder="e.g., Labrador Retriever")
    dog_weight = st.number_input("Weight (kg):", min_value=0.1, max_value=100.0, step=0.5, value=10.0, key='dog_weight')
    dog_age = st.number_input("Age (years):", min_value=0.1, max_value=30.0, step=0.5, value=1.0, key='dog_age')
    dog_activity = st.selectbox(
        "Activity Level:",
        ('Low (Less than 1 hour exercise/day)', 'Moderate (1-2 hours exercise/day)', 'High (More than 2 hours exercise/day)', 'Working/Very High'),
        key='dog_activity'
    )
    dog_allergies_str = st.text_input("Known Allergies (comma-separated):", key='dog_allergies', placeholder="e.g., chicken, beef, grain (Leave blank if none)")
    dog_additional_info = st.text_area("Additional Information (Optional):", key='dog_additional_info', placeholder="e.g., Sensitive stomach...")

    # --- Add Password Field ---
    app_password_input = st.text_input("Enter Password to Get AI Recommendation:", type="password", key="app_password_input")
    # --- End Password Field ---

    st.divider()
    submit_button = st.button("Get Recommendation", key='submit_button', type="primary")

# --- Output Column ---
with output_col:
    st.header("Analysis & Recommendation")
    if submit_button:
        barcode_to_process = None
        with st.spinner('Processing barcode input...'):
            if uploaded_file is not None:
                barcode_to_process = process_image_input(uploaded_file)
            elif camera_photo is not None:
                barcode_to_process = process_image_input(camera_photo)
            elif manual_barcode:
                barcode_to_process = manual_barcode
                st.success(f"Using Manual Barcode: {barcode_to_process}")
            else:
                st.warning("Please provide a barcode via image upload, webcam, or manual entry.")

        if barcode_to_process:
            dog_allergies_list = [allergy.strip() for allergy in dog_allergies_str.split(',') if allergy.strip()]
            dog_info_dict = {
                "breed": dog_breed, "age": dog_age, "weight_kg": dog_weight,
                "activity": dog_activity, "allergies": dog_allergies_list,
                "additional_info": dog_additional_info
            }
            if not dog_breed or not dog_age or not dog_weight:
                 st.warning("Please provide at least the dog's breed, age, and weight for better recommendations.")

            nutrition_info = None
            ai_recommendation = None
            with st.spinner(f'Fetching nutrition data for {barcode_to_process}...'):
                try:
                    nutrition_info = get_nutrition_data(barcode_to_process)
                except Exception as e:
                    st.error(f"Error fetching nutrition data: {e}")

            if nutrition_info:
                st.subheader("Nutrition Information")
                display_info = {k: v for k, v in nutrition_info.items() if v is not None}
                try:
                    df_nutrition = pd.DataFrame(display_info.items(), columns=['Nutrient / Fact', 'Value'])
                    df_nutrition = df_nutrition[df_nutrition['Nutrient / Fact'] != 'schema_version'].copy()
                    if 'Value' in df_nutrition.columns: # Check if 'Value' column exists
                        df_nutrition['Value'] = df_nutrition['Value'].astype(str)
                    st.dataframe(df_nutrition, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Could not display nutrition data as table: {e}")
                    st.json(display_info)

                # --- Password Check before AI Call ---
                if not CORRECT_PASSWORD:
                    st.error("Application password is not configured by the administrator. AI recommendations disabled.")
                elif app_password_input == CORRECT_PASSWORD:
                    with st.spinner('Generating AI recommendation...'):
                        try:
                            ai_recommendation = ai_model.create_response(nutrition_info, dog_info_dict)
                            st.subheader("AI Veterinarian Recommendation")
                            st.markdown(ai_recommendation)
                        except Exception as e:
                            st.error(f"Error generating AI recommendation: {e}")
                    if ai_recommendation:
                        try:
                             log_interaction(barcode_to_process, dog_info_dict, nutrition_info, ai_recommendation)
                             st.info("Interaction logged successfully.")
                        except Exception as e:
                             st.error(f"Failed to log interaction: {e}")
                elif app_password_input: # If password was entered but is wrong
                    st.error("Incorrect password. AI recommendation will not be generated.")
                else: # If password field was left blank
                    st.warning("Password required to generate AI recommendation.")
                # --- End Password Check ---

            elif not nutrition_info and barcode_to_process:
                st.error(f"Could not find nutrition information for barcode: {barcode_to_process}")
        elif not any([uploaded_file, camera_photo, manual_barcode]):
             pass
    else:
        st.info("Provide food barcode, your dog's details, then click 'Get Recommendation'.")

# --- Optional: Display Log File Content (remains the same) ---
st.divider()
show_log = st.expander("Show Application Log (for debugging)")
with show_log:
    try:
        if os.path.exists(LOG_FILE):
             with open(LOG_FILE, 'r') as f:
                log_content = f.read()
                st.text_area("Log Content:", log_content, height=300, key='log_display')
        else:
             st.text("Log file not created yet. Submit data first.")
    except Exception as e:
        st.error(f"Could not read log file: {e}")
