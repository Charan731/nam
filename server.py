import os
import json
import hmac
import hashlib
from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# Load env variables
MONGO_URI = os.getenv("MONGO_URI")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
PORT = int(os.getenv("PORT", 5000))

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client['ram']
collection = db['raj']

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify Razorpay signature
    received_sig = request.headers.get('X-Razorpay-Signature')
    body = request.data.decode('utf-8')
    expected_sig = hmac.new(WEBHOOK_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()

    if received_sig != expected_sig:
        return jsonify({'status': 'invalid signature'}), 400

    payload = json.loads(body)
    if payload['event'] == 'payment.captured':
        payment_id = payload['payload']['payment']['entity']['id']

        # Assuming Name & Place are passed as notes
        name = payload['payload']['payment']['entity'].get('notes', {}).get('name', 'Anonymous')
        place = payload['payload']['payment']['entity'].get('notes', {}).get('place', 'Unknown')

        timestamp = datetime.utcnow()
        order = collection.count_documents({}) + 1

        collection.insert_one({
            'payment_id': payment_id,
            'name': name,
            'place': place,
            'timestamp': timestamp,
            'order': order
        })

        return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'ignored'}), 200

@app.route('/get-names')
def get_names():
    names = list(collection.find({}, {'_id': 0}).sort('order', 1))
    return jsonify(names)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
