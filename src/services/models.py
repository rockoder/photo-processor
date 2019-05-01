import datetime

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import TIMESTAMP

from web import db
from status import Status

class PhotoThumbnail(db.Model):
  __tablename__ = 'photo_thumbnails'

  uuid = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
  photo_uuid = db.Column(UUID(as_uuid=True))
  width = db.Column(db.SmallInteger)
  height = db.Column(db.SmallInteger)
  url = db.Column(db.Text)
  created_at = db.Column(TIMESTAMP(), default=datetime.datetime.utcnow)

  def insert(self):
    db.session.add(self)
    db.session.commit()

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

  uuid = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
  url = db.Column(db.Text)  
  status = db.Column(ENUM(Status, name="photo_status", create_type=False))
  created_at = db.Column(TIMESTAMP(), default=datetime.datetime.utcnow)

  def __init__(self, uuid, url, status, created_at):
    self.uuid = uuid
    self.url = url
    self.status = status
    self.created_at = created_at

  def update_status(self, new_status):
    self.status = new_status
    db.session.commit()

  def __repr__(self):
    return '<id {}>'.format(self.uuid)

  def serialize(self):
    return {
      'uuid': self.uuid, 
      'url': self.url,
      'status': self.status,
      'created_at':self.created_at
    }
