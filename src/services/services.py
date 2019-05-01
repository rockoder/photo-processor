import os

from kombu import Connection, Exchange, Queue, Producer, Consumer, eventloop
from urllib.request import urlretrieve
from urllib.parse import urlparse
from PIL import Image
from status import Status
import models

exchange = Exchange('photo-processor', type='direct')
queue = Queue('photo-processor', exchange, routing_key='photo-processor')

def send_message(uuid):
  with Connection(os.environ['AMQP_URI']) as connection:
    producer = Producer(connection)
    producer.publish({'uuid': uuid}, 
      exchange=exchange,
      routing_key='photo-processor',
      serializer='json',
      declare=[exchange, queue])

def message_listener():
  with Connection(os.environ['AMQP_URI']) as connection:
      with Consumer(connection, queue, callbacks=[receive_message]):
        for _ in eventloop(connection):
          pass

# This is the callback applied when a message is received.
def receive_message(body, message):
  message.ack()

  try:
    photo=models.Photo.query.filter_by(uuid=body['uuid']).first()

    photo.update_status(Status.processing)
    generate_thumbnail(photo)
    photo.update_status(Status.completed)

  except Exception as e:
    print(e.__doc__)
    photo.update_status(Status.failed)

def generate_thumbnail(photo):
  thumbnail_dir="/waldo-app-thumbs/"

  size = 320, 320
  infile, header = urlretrieve(photo.url)
  im = Image.open(infile)
  im.thumbnail(size)
  orgfile = os.path.basename(urlparse(photo.url).path)
  im.save(thumbnail_dir + orgfile, "JPEG")

  thumbnail = models.PhotoThumbnail(photo_uuid=photo.uuid, 
    width=im.width,
    height=im.height,
    url=thumbnail_dir + orgfile)

  thumbnail.insert()

def get_pending_photos():
  return models.Photo.query.filter_by(status=Status.pending)
