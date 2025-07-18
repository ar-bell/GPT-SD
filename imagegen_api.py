from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os, io, base64, uuid, logging, traceback
from PIL import Image
from google import genai
from google.genai import types
import datetime

app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # MAKE SURE KEY IS IN ENV VARIABLES
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is required")
client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODELS = {
    'gemini-native': 'gemini-2.0-flash-preview-image-generation',
    'imagen-3': 'imagen-3.0-generate-002',
    'imagen-4': 'imagen-4.0-generate-preview-06-06',
    'imagen-4-ultra': 'imagen-4.0-ultra-generate-preview-06-06'
}

def validate_prompt(prompt):
    if not prompt or not isinstance(prompt, str):
        return False, "Prompt must be a non-empty string"
    if len(prompt) > 2000:
        return False, "Prompt too long (max 2000 chars)"
    return True, ""

def save_image_to_buffer(image_data, format='PNG'):
    if isinstance(image_data, str):
        image_data = base64.b64decode(image_data)
    img = Image.open(io.BytesIO(image_data))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'available_models': list(GEMINI_MODELS.keys())
    })

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.get_json(force=True)
        prompt = data.get('prompt', '')
        model_type = data.get('model', 'gemini-native')

        is_valid, msg = validate_prompt(prompt)
        if not is_valid:
            return jsonify({'error': msg}), 400
        if model_type not in GEMINI_MODELS:
            return jsonify({'error': 'Invalid model'}), 400

        model_name = GEMINI_MODELS[model_type]

        if model_type == 'gemini-native':
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=['TEXT','IMAGE'])
            )
            images = []
            text_resp = ""
            part = response.candidates[0].content.parts
            for p in part:
                if p.text: text_resp = p.text
                if p.inline_data:
                    img_b64 = base64.b64encode(p.inline_data.data).decode()
                    images.append({'data': img_b64, 'mime_type': p.inline_data.mime_type or 'image/png'})
            return jsonify({'success': True, 'images': images, 'text': text_resp})

        else:
            cfg = types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio='1:1',
                person_generation='allow_adult'
            )
            response = client.models.generate_images(model=model_name, prompt=prompt, config=cfg)
            imgs = []
            for img in response.generated_images:
                b64 = base64.b64encode(img.image.image_bytes).decode()
                imgs.append({'data': b64, 'mime_type': 'image/png'})
            return jsonify({'success': True, 'images': imgs})

    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Server error'}), 500

@app.route('/generate-image-file', methods=['POST'])
def generate_image_file():
    try:
        data = request.get_json(force=True)
        prompt = data.get('prompt', '')
        model_type = data.get('model', 'gemini-native')
        is_valid, msg = validate_prompt(prompt)
        if not is_valid or model_type not in GEMINI_MODELS:
            return jsonify({'error': msg or 'Invalid model'}), 400

        response = client.models.generate_content(
            model=GEMINI_MODELS[model_type],
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=['IMAGE'])
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                buf = save_image_to_buffer(part.inline_data.data)
                fname = f'gen_img_{uuid.uuid4().hex[:8]}.png'
                return send_file(buf, mimetype='image/png', as_attachment=True, download_name=fname)
        return jsonify({'error': 'No image generated'}), 500

    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Server error'}), 500

@app.route('/models', methods=['GET'])
def get_models():
    return jsonify({'models': list(GEMINI_MODELS.keys())})

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_err(e):
    return jsonify({'error': 'Server error'}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

