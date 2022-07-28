#!/usr/bin/env python3
"""
Author: Alexander
Description: This script will prepare a couple of things and then start the server
"""
from dotenv import load_dotenv
import os
import shutil

if not os.path.exists(".env"):
    print("No .env file. Copying .env.example over for you")
    shutil.copy(".env.example", ".env")

try:
    os.makedirs('fullstack/static/images')
except FileExistsError:
    pass

load_dotenv(dotenv_path=".env")

from fullstack import app
app.run(debug=True)
