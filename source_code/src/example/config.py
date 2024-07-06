import os

MONGO_USER = os.getenv('MONGO_USER', 'testapp')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'testapp')
MONGO_DB = os.getenv('MONGO_DB', 'testapp')
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = os.getenv('MONGO_PORT', '27017')

MONGO_URI = f'mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin'

if not all([MONGO_USER, MONGO_PASSWORD, MONGO_DB, MONGO_HOST, MONGO_PORT]):
    raise ValueError("One or more environment variables for MongoDB connection are not set.")
