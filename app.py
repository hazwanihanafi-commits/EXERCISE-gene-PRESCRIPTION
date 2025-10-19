from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_cors import CORS
import json, os, io
from fpdf import FPDF
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
RULES_PATH = os.path.join(BASE_DIR, "rules.json")
ASSESS_PATH = os.path.join(BASE_DIR, "assessments.json")

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

@app.route('/')
def home():
    return "Welcome to EXECOGIM Gene-Guided Exercise API — Server Running ✅"

# (keep the rest of your code: rules, endpoints, PDFs, etc.)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
