from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import openai
from google.cloud import storage
import firebase
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv('OPENAI_API_KEY')

# Function to upload the image to Google Cloud Storage


def upload_to_firebase_storage(image_path, bucket_name, destination_blob_name):
    # Initialize a client
    storage_client = storage.Client()
    # Reference the bucket
    bucket = storage_client.bucket(bucket_name)
    # Create a new blob (object)
    blob = bucket.blob(destination_blob_name)
    # Upload the file to the blob
    blob.upload_from_filename(image_path)
    # Make the blob publicly accessible
    blob.make_public()
    return blob.public_url


@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files['image']
    filename = secure_filename(image.filename)
    image_path = os.path.join("/tmp", filename)
    image.save(image_path)

    # Upload image to Firebase Storage
    bucket_name = "daily-j.appspot.com"
    destination_blob_name = f"uploads/{filename}"
    public_url = upload_to_firebase_storage(
        image_path, bucket_name, destination_blob_name)

    with open(image_path, 'rb') as img_file:
        image_data = img_file.read()

    response = openai.Image.create(
        image=image_data,
        instructions="""
        Please analyze the image and return a JSON object with the following keys:
        1. title - A string that provides a title for the meal.
        2. ingredients - A list of dictionaries representing an ingredient object, where each object contains a key: 
            "name": is the name of an ingredient visible in the meal, 
            "quantity": the quantity of the ingredient in grams,
            "unit": the unit of measurement for the quantity (e.g., grams, milliliters, etc.),
        3. nutritional_information - A dictionary with keys as each of the following common nutritional values:
        - CaloriesKcal
        - Carbs
        - Sugar
        - DietaryFiber
        - Sodium
        - Fat
        - FatSaturated
        - FatMonounsaturated
        - FatPolyunsaturated
        - FatTrans
        - Protein
        - Cholesterol
        - VitaminA
        - VitaminC
        - Calcium
        - Iron
        - Magnesium
        - Zinc
        - Potassium
        - Salt
        - Biotin
        - Omega3
        and values as floats representing the amount of each nutrient in grams with -1.0 if unknown.
        """
    )

    result = response['choices'][0]['message']['content']
    return jsonify({
        "result": result,
        "image_url": public_url
    }), 200


@app.route('/version', methods=['GET'])
def get_version():
    return jsonify({"version": os.environ.get("APP_VERSION", "1.0.0")}), 200


@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({"status": "running"}), 200


@app.route('/get_nutritional_values_for_ingredient', methods=['GET'])
def get_nutritional_values_for_ingredient():
    ingredient_name = request.args.get('ingredient_name')
    if not ingredient_name:
        return jsonify({'error': 'No ingredient name provided'}), 400

    # Prepare the prompt for ChatGPT
    prompt = f"""
    The user has provided the name of an ingredient: {ingredient_name}

    Please provide the nutritional values for the ingredient {ingredient_name} in a JSON object with the following keys:
    nutritional_information - A dictionary with keys as each of the following common nutritional values with each being the float value per 100g of the ingredient:
        - CaloriesKcal
        - Carbs
        - Sugar
        - DietaryFiber
        - Sodium
        - Fat
        - FatSaturated
        - FatMonounsaturated
        - FatPolyunsaturated
        - FatTrans
        - Protein
        - Cholesterol
        - VitaminA
        - VitaminC
        - Calcium
        - Iron
        - Magnesium
        - Zinc
        - Potassium
        - Salt
        - Biotin
        - Omega3
    """
    # Get the completion from ChatGPT
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a nutrition expert."},
            {"role": "user", "content": prompt}
        ]
    )

    result = response['choices'][0]['message']['content']

    return jsonify({'result': result}), 200


# @app.route('/upload_voice_note', methods=['POST'])
# def upload_voice_note():
#     if 'voice_note' not in request.files:
#         return jsonify({'error': 'No voice note provided'}), 400

#     voice_note = request.files['voice_note']
#     ingredients_data = request.form.get('ingredients_data')

#     if not ingredients_data:
#         return jsonify({'error': 'No ingredients data provided'}), 400

#     try:
#         ingredients_data = eval(ingredients_data)
#     except:
#         return jsonify({'error': 'Invalid ingredients data format'}), 400

#     # Transcribe the voice note using OpenAI Whisper
#     transcription_response = openai.Audio.transcribe("whisper-1", voice_note)
#     transcription_text = transcription_response['text']

#     # Prepare the prompt for ChatGPT
#     prompt = f"""
#     The following is a transcription of a user's voice note describing their meal:
#     {transcription_text}

#     The user has provided the following list of ingredients and the number of times they have been logged:
#     {ingredients_data}

#     Using the entire context of the voice note, please provide the most likely amounts for each ingredient mentioned in the voice note. If serving sizes are explicitly mentioned, use them. If not, use expected serving sizes based on the context.

#     Return the response as a JSON object with the following keys:
#     1. title - A string that provides a title for the meal.
#     2. ingredients - A list of strings, where each string is the name of an ingredient visible in the meal.
#     3. Nutritional Information - A dictionary with keys as common nutritional values (e.g., 'Protein', 'Carbohydrates', 'Fats', etc.) and values as floats representing the amount of each nutrient in grams.
#     """

#     # Get the completion from ChatGPT
#     response = openai.ChatCompletion.create(
#         model="gpt-4",
#         messages=[
#             {"role": "system", "content": "You are a nutrition expert."},
#             {"role": "user", "content": prompt}
#         ]
#     )

#     return jsonify(response['choices'][0]['message']['content'])

@app.route('/upload_voice_note', methods=['POST'])
def upload_voice_note():
    if 'voice_note' not in request.files:
        return jsonify({'error': 'No voice note provided'}), 400

    # Get the flag to determine the type of processing required
    process_type = request.form.get('process_type')
    if process_type not in ['ingredients', 'nutritional_values', 'food_log']:
        return jsonify({'error': 'Invalid process type'}), 400

    voice_note = request.files['voice_note']

    # Transcribe the voice note using OpenAI Whisper
    transcription_response = openai.Audio.transcribe("whisper-1", voice_note)
    transcription_text = transcription_response['text']

    if process_type == 'food_log':
        # Prepare the prompt for processing food logs
        prompt = f"""
        The following is a transcription of a user's voice note describing their meal:
        {transcription_text}

        Using the entire context of the voice note, please provide the most likely amounts for each ingredient mentioned in the voice note. If serving sizes are explicitly mentioned, use them. If not, use expected serving sizes based on the context.

        Return the response as a JSON object with the following keys:
        1. title - A string that provides a title for the meal.
        2. ingredients - A list of dictionaries representing an ingredient object, where each object contains a key: 
            "name": is the name of an ingredient visible in the meal, 
            "quantity": the quantity of the ingredient in grams,
            "unit": the unit of measurement for the quantity (e.g., grams, milliliters, etc.),
        3. nutritional_information - A dictionary with keys as each of the following common nutritional values:
        - CaloriesKcal
        - Carbs
        - Sugar
        - DietaryFiber
        - Sodium
        - Fat
        - FatSaturated
        - FatMonounsaturated
        - FatPolyunsaturated
        - FatTrans
        - Protein
        - Cholesterol
        - VitaminA
        - VitaminC
        - Calcium
        - Iron
        - Magnesium
        - Zinc
        - Potassium
        - Salt
        - Biotin
        - Omega3
        and values as floats representing the amount of each nutrient in grams with -1.0 if unknown.
        """
    elif process_type == 'ingredients':
        # Prepare the prompt for processing ingredients
        prompt = f"""
        The following is a transcription of a user's voice note describing the ingredients on the package of a product:
        {transcription_text}

        Using the entire context of the voice note, list all the ingredients mentioned. 

        Return the response as a JSON object with the following keys:
        1. ingredients - A list of dictionaries that all have a name and a QUID key, where each name key is the name of an ingredient mentioned in the voice note and each QUID key corresponds to the % amount of that ingredient if it is mentioned in the voicenote.
        """

    elif process_type == 'nutritional_values':
        # Prepare the prompt for processing nutritional values
        prompt = f"""
        The following is a transcription of a user's voice note describing the nutritional values of a product:
        {transcription_text}

        Identify the serving size, whether the values extracted are per 100g (serving_size=100g in the result) or per serving (in which case how big is a serving in grams? set the serving_size key to this value in grams). 
        Extract all nutritional values mentioned by returning a JSON object with 2 keys: 1. serving_size as described before with a default of "100g" and 2. nutritional_values which is a dictionary containing keys for each nutritional value:
        - CaloriesKcal
        - Carbs
        - Sugar
        - DietaryFiber
        - Sodium
        - Fat
        - FatSaturated
        - FatMonounsaturated
        - FatPolyunsaturated
        - FatTrans
        - Protein
        - Cholesterol
        - VitaminA
        - VitaminC
        - Calcium
        - Iron
        - Magnesium
        - Zinc
        - Potassium
        - Salt
        - Biotin
        - Omega3
        with values being floats for each key, representing the amount of each nutrient in grams.
        If a value is not mentioned, return -1 for that value.
        """

    # Get the completion from ChatGPT
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a nutrition expert."},
            {"role": "user", "content": prompt}
        ]
    )

    result = {
        "extracted_data": response['choices'][0]['message']['content'],
        "transcription": transcription_text
    }

    return jsonify({'result': result}), 200


@app.route('/upload_image_for_ocr', methods=['POST'])
def upload_image_for_ocr():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files['image']
    filename = secure_filename(image.filename)
    image_path = os.path.join("/tmp", filename)
    image.save(image_path)

    # Get the flag to determine the type of processing required
    process_type = request.form.get('process_type')
    if process_type not in ['ingredients', 'nutritional_values']:
        return jsonify({'error': 'Invalid process type'}), 400

    with open(image_path, 'rb') as img_file:
        image_data = img_file.read()

    if process_type == 'ingredients':
        response = openai.Image.create(
            image=image_data,
            instructions="""
            The following is an image of a product's ingredients label listing the ingredients in the product. Please analyze the image and extract all the ingredients recognised from the image. 

            Return the response as a JSON object with the following keys:
            1. ingredients - A list of dictionaries that all have a name and a QUID key, where each name key is the name of an ingredient mentioned in the voice note and each QUID key corresponds to the % amount of that ingredient if it is mentioned in the voicenote.
            """
        )

    elif process_type == 'nutritional_values':
        response = openai.Image.create(
            image=image_data,
            instructions="""
            The following is an image of a product's nutritional information label describing the nutritional values of the product. Please analyze the image and extract all the nutritional values recognised from the image. 

            Return the response as a JSON object with the following keys:
            1. ingredients - A list of dictionaries that all have a name and a QUID key, where each name key is the name of an ingredient mentioned in the voice note and each QUID key corresponds to the % amount of that ingredient if it is mentioned in the voicenote.
            Identify the serving size, whether the values extracted are per 100g (serving_size=100g in the result) or per serving (in which case how big is a serving in grams? set the serving_size key to this value in grams). 
            Extract all nutritional values mentioned by returning a JSON object with 2 keys: 1. serving_size as described before with a default of "100g" and 2. nutritional_values which is a dictionary containing keys for each nutritional value:
            - CaloriesKcal
            - Carbs
            - Sugar
            - DietaryFiber
            - Sodium
            - Fat
            - FatSaturated
            - FatMonounsaturated
            - FatPolyunsaturated
            - FatTrans
            - Protein
            - Cholesterol
            - VitaminA
            - VitaminC
            - Calcium
            - Iron
            - Magnesium
            - Zinc
            - Potassium
            - Salt
            - Biotin
            - Omega3

            If a value is not mentioned, return -1 for that value.
            """
        )
    else:
        return jsonify({'error': 'Invalid process type'}), 400

    result = response['choices'][0]['message']['content']
    return jsonify({
        "result": result,
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
