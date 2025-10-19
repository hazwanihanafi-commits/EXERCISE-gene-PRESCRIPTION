from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_cors import CORS
import json, os, io
from fpdf import FPDF
from datetime import datetime

# === Configuration ===
BASE_DIR = os.path.dirname(__file__)
RULES_PATH = os.path.join(BASE_DIR, "rules.json")
ASSESS_PATH = os.path.join(BASE_DIR, "assessments.json")

# ✅ Only one Flask app instance
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# === Utility functions ===
def load_rules():
    with open(RULES_PATH, "r") as f:
        return json.load(f)

def save_rules(rules):
    with open(RULES_PATH, "w") as f:
        json.dump(rules, f, indent=2)

def load_assessments():
    if not os.path.exists(ASSESS_PATH):
        with open(ASSESS_PATH, "w") as f:
            json.dump({}, f)
    with open(ASSESS_PATH, "r") as f:
        return json.load(f)

def save_assessments(data):
    with open(ASSESS_PATH, "w") as f:
        json.dump(data, f, indent=2)

# === Core logic ===
def generate_plan_from_input(data, rules):
    genotype = data.get("genotype", "Met")
    age = int(data.get("age", 40))
    fitness = data.get("fitness_level", "moderate")

    if genotype.lower().startswith("val"):
        template = rules.get("Val/Val") or rules.get("Val") or rules.get("ValVal")
        label = "Val/Val"
    else:
        template = rules.get("Met") or rules.get("Met allele") or rules.get("Met")
        label = "Met carrier"

    if template is None:
        template = {
            "sessions_per_week": 4,
            "session_length_min": 30,
            "intensity": "moderate",
            "aerobic_ratio": 0.5,
            "strength_ratio": 0.3,
            "mindbody_ratio": 0.2
        }

    sessions_per_week = template.get("sessions_per_week", 4)
    session_length = template.get("session_length_min", 30)
    intensity = template.get("intensity", "moderate")

    # Build 12-week plan
    weeks = []
    for wk in range(1, 13):
        sessions = []
        increase_duration = 0
        complexity = 0
        if label == "Val/Val":
            if wk in [4, 8, 11]:
                complexity = 1
        else:
            if wk in [4, 7, 10]:
                increase_duration = 5

        for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
            if label == "Val/Val":
                if d=="Mon": typ="HIIT"; dur=session_length + increase_duration
                elif d=="Tue": typ="Resistance"; dur=int((session_length*0.9)+increase_duration)
                elif d=="Wed": typ="Skill/Dual-task"; dur=int((session_length*0.8)+increase_duration)
                elif d=="Thu": typ="Active Recovery"; dur=20
                elif d=="Fri": typ="Mixed Cardio-Strength"; dur=session_length + increase_duration
                elif d=="Sat": typ="Optional Sport"; dur=30
                else: typ="Rest"; dur=0
            else:
                if d=="Mon": typ="Endurance (steady)"; dur=session_length + increase_duration
                elif d=="Tue": typ="Strength+Balance"; dur=int((session_length*0.8)+increase_duration)
                elif d=="Wed": typ="Adventure Mode"; dur=20 + increase_duration
                elif d=="Thu": typ="Yoga/Tai Chi"; dur=30
                elif d=="Fri": typ="Endurance intervals"; dur=session_length + increase_duration
                elif d=="Sat": typ="Light aerobic + memory"; dur=30
                else: typ="Rest"; dur=0
            sessions.append({"day":d, "type":typ, "duration_min":dur})
        weeks.append({"week":wk, "sessions":sessions})

    return {
        "genotype_label": label,
        "summary": {
            "sessions_per_week": sessions_per_week,
            "session_length_min": session_length,
            "intensity": intensity,
            "notes": template.get("notes","")
        },
        "weeks": weeks,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

# === Health check (for Render) ===
@app.route('/health')
def health():
    return jsonify(status="ok", message="Render health check passed ✅"), 200

# === API routes ===
@app.route('/api')
def api_home():
    return "✅ EXECOGIM Gene-Guided Exercise API is running."

@app.route("/api/generate_plan", methods=["POST"])
def api_generate_plan():
    data = request.json or {}
    rules = load_rules()
    plan = generate_plan_from_input(data, rules)
    return jsonify(plan)

@app.route("/api/save_assessment", methods=["POST"])
def api_save_assessment():
    data = request.json or {}
    pid = data.get("participant_id") or data.get("participant_name") or "unknown"
    atype = data.get("assessment_type","pre")
    assessments = load_assessments()
    if pid not in assessments:
        assessments[pid] = {}
    assessments[pid][atype] = data.get("measures", {})
    assessments[pid].setdefault("_meta", {})
    assessments[pid]["_meta"][atype] = {"date": data.get("date") or datetime.utcnow().strftime("%Y-%m-%d")}
    save_assessments(assessments)
    return jsonify({"status":"ok", "participant": pid, "type": atype})

@app.route("/api/get_assessment/<participant_id>", methods=["GET"])
def api_get_assessment(participant_id):
    assessments = load_assessments()
    return jsonify(assessments.get(participant_id, {}))

# === Admin Editor ===
@app.route("/admin", methods=["GET","POST"])
def admin():
    key = request.args.get("key","")
    if key != "admin":
        return "Provide ?key=admin to access admin editor (demo)."
    if request.method=="POST":
        new_rules = request.form.get("rules")
        try:
            parsed = json.loads(new_rules)
            save_rules(parsed)
            return redirect(url_for("admin", key="admin"))
        except Exception as e:
            return f"Error parsing JSON: {e}"
    with open(RULES_PATH,"r") as f:
        current = f.read()
    return render_template("admin.html", rules_json=current)

# === Frontend / Default Route ===
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    # Serve files if they exist in /static
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # If no static index.html, show default message
    index_path = os.path.join(app.static_folder, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, "index.html")
    return """
    <h2>EXECOGIM Gene-Guided Exercise API</h2>
    <p>Server Running ✅</p>
    <p>Try the <a href='/api'>/api</a> endpoint.</p>
    """

# === Start Server (Render will use gunicorn app:app) ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
