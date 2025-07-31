from flask import Flask, request, jsonify, send_file
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import os, io
app = Flask(__name__)

API_KEY = os.getenv("IBM_TTS_API_KEY")
SERVICE_URL = os.getenv("IBM_TTS_URL")
if not (API_KEY and SERVICE_URL):
    raise RuntimeError("Set IBM_TTS_API_KEY and IBM_TTS_URL env variables")

authenticator = IAMAuthenticator(API_KEY)
tts = TextToSpeechV1(authenticator=authenticator)
tts.set_service_url(SERVICE_URL)


@app.route("/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json()
    text = data.get("text")
    voice = data.get("voice", "en-US_AllisonV3Voice")

    if not text or not isinstance(text, str):
        return jsonify({"error": "Missing or invalid 'text'"}), 400

    try:
        response = tts.synthesize(
            text,
            voice=voice,
            accept="audio/mp3"
        ).get_result()
        audio_bytes = response.content
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/mp3",
            as_attachment=False,
            download_name="speech.mp3"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

