import os
from mongoengine import Document, StringField, IntField, connect

connect(host=os.getenv('MONGO_URI', 'mongodb://localhost:27017/mydatabase'))

class Car(Document):
    meta = {'collection': 'car_collection'}
    id = IntField(primary_key=True)
    name = StringField(max_length=100)
    price = IntField()
    year = StringField(max_length=100)

    def to_dict(self):
        """Convert the document to a dictionary and rename `_id` to `id`."""
        data = self.to_mongo().to_dict()
        data['id'] = data.pop('_id')
        return data
