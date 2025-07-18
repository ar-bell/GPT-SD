from flask import Flask, request, jsonify
from flask_cors import CORS
import os, io, base64, uuid, logging
from PIL import Image
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # REMEMBER TO ADD KEY
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is required")

client = genai.Client(api_key=GEMINI_API_KEY)

@app.route("/generate-image", methods=["POST"])
def generate_image():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )
        part = next(p for p in resp.candidates[0].content.parts if p.inline_data)
        img_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
        return jsonify({
            "image_b64": img_b64,
            "generation_id": str(uuid.uuid4())
        })
    except Exception as e:
        logging.error("Image generation error", exc_info=e)
        return jsonify({"error": "Failed to generate image"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)


