from flask import Flask, jsonify, request
import requests
import os
import sys

# Use the environment variable for the port, defaulting to 5003 if not provided
port = int(os.getenv("FLASK_RUN_PORT", 5003))

app = Flask(__name__)
