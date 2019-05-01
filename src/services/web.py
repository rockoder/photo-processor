import os
import threading

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

import services

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['PG_CONNECTION_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
db.init_app(app)

@app.before_first_request
def activate_job():
  thread = threading.Thread(target=services.message_listener)
  thread.start()

@app.route("/")
def index():
  return jsonify(success=True)

@app.route("/photos/pending")
def pendingPhotos():
  try:
    photos=services.get_pending_photos()
    return  jsonify([p.serialize() for p in photos])
  except Exception as e:
    return(str(e))

@app.route("/photos/process", methods=['POST'])
def processPhotos():
  uuids = request.get_json()['uuids']
  for uuid in uuids:
    services.send_message(uuid)
  return jsonify(uuids)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
