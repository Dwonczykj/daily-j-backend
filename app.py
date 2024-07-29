from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv('OPENAI_API_KEY')


@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files['image']
    filename = secure_filename(image.filename)
    image_path = os.path.join("/tmp", filename)
    image.save(image_path)

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
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(debug=True)
