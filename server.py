from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from dotenv import load_dotenv
import razorpay
import os
import hashlib
import hmac
import json
from datetime import datetime
from flask_cors import CORS

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
PORT = int(os.getenv("PORT", 5000))

# Flask App Setup
app = Flask(__name__)
CORS(app)

# MongoDB Connection
client = MongoClient(MONGO_URI)
db = client["ram"]
collection = db["raj"]

# Home route
@app.route('/')
def home():
    return render_template("index.html")

# Get names
@app.route('/get-names', methods=['GET'])
def get_names():
    names = list(collection.find({}, {'_id': 0}))
    names_sorted = sorted(names, key=lambda x: x['order'])
    return jsonify(names_sorted)

# Razorpay Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    signature = request.headers.get('X-Razorpay-Signature')

    # Verify signature
    expected = hmac.new(
        bytes(WEBHOOK_SECRET, 'utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(expected, signature):
        data = json.loads(payload)
        if data['event'] == 'payment.captured':
            notes = data['payload']['payment']['entity'].get('notes', {})
            name = notes.get('name')
            place = notes.get('place')

            if name and place:
                count = collection.count_documents({})
                document = {
                    "payment_id": data['payload']['payment']['entity']['id'],
                    "name": name,
                    "place": place,
                    "timestamp": datetime.utcnow().isoformat(),
                    "order": count + 1
                }
                collection.insert_one(document)
                return jsonify({"status": "success"}), 200
        return jsonify({"status": "ignored"}), 200
    else:
        return jsonify({"status": "unauthorized"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
