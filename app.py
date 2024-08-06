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
        2. ingredients - A list of strings, where each string is the name of an ingredient visible in the meal.
        3. Nutritional Information - A dictionary with keys as common nutritional values (e.g., 'Protein', 'Carbohydrates', 'Fats', etc.) and values as floats representing the amount of each nutrient in grams.
        """
    )

    result = response['choices'][0]['message']['content']
    return jsonify({
        "result": result,
        "image_url": public_url
    }), 200


@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "Flask app is running"}), 200


@app.route('/upload_voice_note', methods=['POST'])
def upload_voice_note():
    if 'voice_note' not in request.files:
        return jsonify({'error': 'No voice note provided'}), 400

    voice_note = request.files['voice_note']
    ingredients_data = request.form.get('ingredients_data')

    if not ingredients_data:
        return jsonify({'error': 'No ingredients data provided'}), 400

    try:
        ingredients_data = eval(ingredients_data)
    except:
        return jsonify({'error': 'Invalid ingredients data format'}), 400

    # Transcribe the voice note using OpenAI Whisper
    transcription_response = openai.Audio.transcribe("whisper-1", voice_note)
    transcription_text = transcription_response['text']

    # Prepare the prompt for ChatGPT
    prompt = f"""
    The following is a transcription of a user's voice note describing their meal:
    {transcription_text}

    The user has provided the following list of ingredients and the number of times they have been logged:
    {ingredients_data}

    Using the entire context of the voice note, please provide the most likely amounts for each ingredient mentioned in the voice note. If serving sizes are explicitly mentioned, use them. If not, use expected serving sizes based on the context.

    Return the response as a JSON object with the following keys:
    1. title - A string that provides a title for the meal.
    2. ingredients - A list of strings, where each string is the name of an ingredient visible in the meal.
    3. Nutritional Information - A dictionary with keys as common nutritional values (e.g., 'Protein', 'Carbohydrates', 'Fats', etc.) and values as floats representing the amount of each nutrient in grams.
    """

    # Get the completion from ChatGPT
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a nutrition expert."},
            {"role": "user", "content": prompt}
        ]
    )

    return jsonify(response['choices'][0]['message']['content'])


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
