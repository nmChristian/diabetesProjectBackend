"""
Author: Alexander
Description: The main file of the program importing everything and setting global variables
"""
from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
import os
import mongomock

app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "secret_key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.url_map.strict_slashes = False
if os.getenv("TESTING") == "TRUE":
    mongo_client = mongomock.MongoClient()
else:
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client[os.getenv("MONGO_DB_NAME")]
DEFAULT_GLYCEMIC_RANGES = [3.0, 3.9, 10.0, 13.9]
DEFAULT_GLYCEMIC_TARGETS = [0.01, 0.04, 0.7, 0.25, 0.05]

from fullstack.views import *

UserView.register(app, route_base="/api/v1/user")
DataView.register(app, route_base="/api/v1/data")
DiagnosisView.register(app, route_base="/api/v1/diagnosis")
NoteView.register(app, route_base="/api/v1/note")
