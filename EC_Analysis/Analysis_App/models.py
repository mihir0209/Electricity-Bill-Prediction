# models.py

from mongoengine import Document, StringField, BooleanField
from bson import ObjectId

class User(Document):
    id = ObjectId()  # Unique identifier for the user (MongoDB ObjectId)
    username = StringField(max_length=150, unique=True, required=True)
    email = StringField(max_length=255, unique=True, required=True)
    password = StringField(required=True)

    def __str__(self):
        return f"User {self.username}, Email: {self.email}"
