from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from enum import Enum
import sys
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['PG_CONNECTION_URI']
db = SQLAlchemy(app)

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import TIMESTAMP

from sqlalchemy import text

class Status(str, Enum):
    pending = 'pending'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'

class PhotoThumbnail(db.Model):
    __tablename__ = 'photo_thumbnails'

    uuid = db.Column(UUID(as_uuid=True), primary_key = True, server_default=text("gen_random_uuid()"))
    photo_uuid = db.Column(UUID(as_uuid=True))
    width = db.Column(db.SmallInteger)
    height = db.Column(db.SmallInteger)
    url = db.Column(db.Text)
    created_at = db.Column(TIMESTAMP(), default=datetime.datetime.utcnow)

    # def __init__(self, photo_uuid, width, height, url):
    #     # self.uuid = uuid
    #     self.photo_uuid = photo_uuid
    #     self.width = width
    #     self.height = height
    #     self.url = url
    #     # self.created_at = created_at

    def __repr__(self):
        return '<id {}>'.format(self.uuid)

    def serialize(self):
        return {
            'uuid': self.uuid, 
            'photo_uuid': self.photo_uuid,
            'width': self.width,
            'height': self.height,
            'url': self.url,
            'created_at':self.created_at
        }

class Photo(db.Model):
    __tablename__ = 'photos'

    uuid = db.Column(UUID(as_uuid=True), primary_key = True)
    url = db.Column(db.Text)  
    status = db.Column(ENUM(Status,
      name="photo_status", create_type=False))
    created_at = db.Column(TIMESTAMP())

    def __init__(self, uuid, url, status, created_at):
        self.uuid = uuid
        self.url = url
        self.status = status
        self.created_at = created_at

    def __repr__(self):
        return '<id {}>'.format(self.uuid)

    def serialize(self):
        return {
            'uuid': self.uuid, 
            'url': self.url,
            'status': self.status,
            'created_at':self.created_at
        }

@app.route("/")
def index():
  return jsonify(success=True)

from kombu import Connection, Exchange, Queue, Producer, Consumer, eventloop
from pprint import pformat
import threading

exchange = Exchange('photo-processor', type='direct')
queue = Queue('photo-processor', exchange, routing_key='photo-processor')

@app.route("/photos/process", methods=['POST'])
def processPhotos():
  uuids = request.get_json()['uuids']
  for uuid in uuids:
    sendEvent(uuid)
  return jsonify(uuids)

def sendEvent(uuid):
  with Connection(os.environ['AMQP_URI']) as connection:
    producer = Producer(connection)
    producer.publish({'uuid': uuid},
                 exchange=exchange,
                 routing_key='photo-processor',
                 serializer='json', 
                 #compression='zlib',
                 declare=[exchange, queue])

def pretty(obj):
    return pformat(obj, indent=4)

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

from urllib.parse import urlparse

from PIL import Image
import os

#: This is the callback applied when a message is received.
def handle_message(body, message):
  try:
    print("ganesh1")
    print(body)
    uuid = body['uuid']
    photo=Photo.query.filter_by(uuid=uuid).first()
    photo.status=Status.processing
    db.session.commit()
    size = 320, 320
    infile, header = urlretrieve(photo.url)
    file, ext = os.path.splitext(infile)
    im = Image.open(infile)
    im.thumbnail(size)
    orgfile = os.path.basename(urlparse(photo.url).path)
    im.save("/waldo-app-thumbs/" + orgfile, "JPEG")

    thumbnail = PhotoThumbnail(photo_uuid=photo.uuid, width=320, 
      height=320, url="/waldo-app-thumbs/" + orgfile)
    db.session.add(thumbnail)
    db.session.commit()

    photo.status=Status.completed
    db.session.commit()

    message.ack()
  except Exception as e:
    print("ganesh2 execept")
    print(e.__doc__)
    photo.status=Status.failed
    db.session.commit()

    message.ack()

@app.before_first_request
def activate_job():
    def run_job():
      #: Create a connection and a channel.
      #: If hostname, userid, password and virtual_host is not specified
      #: the values below are the default, but listed here so it can
      #: be easily changed.
      with Connection(os.environ['AMQP_URI']) as connection:

          #: Create consumer using our callback and queue.
          #: Second argument can also be a list to consume from
          #: any number of queues.
          with Consumer(connection, queue, callbacks=[handle_message]):

              #: Each iteration waits for a single event.  Note that this
              #: event may not be a message, or a message that is to be
              #: delivered to the consumers channel, but any event received
              #: on the connection.
              for _ in eventloop(connection):
                pass

    # TODO: declare exchange and queue here
    thread = threading.Thread(target=run_job)
    thread.start()

@app.route("/photos/pending")
def pendingPhotos():
    try:
        photos=Photo.query.filter_by(status=Status.pending)
        return  jsonify([e.serialize() for e in photos])
    except Exception as e:
      return(str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
