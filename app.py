from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to EXECOGIM Gene-Guided Exercise API — Server Running ✅"
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

    # Build 12-week plan with progressive adjustments
    weeks = []
    for wk in range(1,13):
        sessions = []
        # progression factors
        increase_duration = 0
        complexity = 0
        if label == "Val/Val":
            # increase complexity earlier, add skill days
            if wk in [4,8,11]:
                complexity = 1
        else:
            # Met carriers: increase duration and sequencing gradually
            if wk in [4,7,10]:
                increase_duration = 5

        for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
            if label == "Val/Val":
                if d=="Mon":
                    typ="HIIT"
                    dur=session_length + increase_duration
                elif d=="Tue":
                    typ="Resistance"
                    dur=int((session_length * 0.9) + increase_duration)
                elif d=="Wed":
                    typ="Skill/Dual-task"
                    dur=int((session_length * 0.8) + increase_duration)
                elif d=="Thu":
                    typ="Active Recovery"
                    dur=20
                elif d=="Fri":
                    typ="Mixed Cardio-Strength"
                    dur=session_length + increase_duration
                elif d=="Sat":
                    typ="Optional Sport"
                    dur=30
                else:
                    typ="Rest"; dur=0
            else:
                if d=="Mon":
                    typ="Endurance (steady)"; dur=session_length + increase_duration
                elif d=="Tue":
                    typ="Strength+Balance"; dur=int((session_length * 0.8) + increase_duration)
                elif d=="Wed":
                    typ="Adventure Mode"; dur=20 + increase_duration
                elif d=="Thu":
                    typ="Yoga/Tai Chi"; dur=30
                elif d=="Fri":
                    typ="Endurance intervals"; dur=session_length + increase_duration
                elif d=="Sat":
                    typ="Light aerobic + memory"; dur=30
                else:
                    typ="Rest"; dur=0
            sessions.append({"day":d, "type":typ, "duration_min":dur})
        weeks.append({"week":wk, "sessions":sessions})

    plan = {
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
    return plan

@app.route("/api/generate_plan", methods=["POST"])
def api_generate_plan():
    data = request.json or {}
    rules = load_rules()
    plan = generate_plan_from_input(data, rules)
    return jsonify(plan)

# Assessments endpoints
@app.route("/api/save_assessment", methods=["POST"])
def api_save_assessment():
    data = request.json or {}
    pid = data.get("participant_id") or data.get("participant_name") or "unknown"
    atype = data.get("assessment_type","pre")  # 'pre' or 'post'
    assessments = load_assessments()
    if pid not in assessments:
        assessments[pid] = {}
    assessments[pid][atype] = data.get("measures", {})
    # store metadata
    assessments[pid].setdefault("_meta", {})
    assessments[pid]["_meta"][atype] = {"date": data.get("date") or datetime.utcnow().strftime("%Y-%m-%d")}
    save_assessments(assessments)
    return jsonify({"status":"ok", "participant": pid, "type": atype})

@app.route("/api/get_assessment/<participant_id>", methods=["GET"])
def api_get_assessment(participant_id):
    assessments = load_assessments()
    return jsonify(assessments.get(participant_id, {}))

@app.route("/api/download_plan_pdf", methods=["POST"])
def download_plan_pdf():
    data = request.json or {}
    rules = load_rules()
    plan = generate_plan_from_input(data, rules)

    participant = data.get("participant_name", "Participant")
    pid = data.get("participant_id", participant.replace(" ","_"))
    dob = data.get("dob", "YYYY-MM-DD")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # If post-assessment exists, compute change vs pre
    assessments = load_assessments()
    pre = assessments.get(pid, {}).get("pre", {})
    post = assessments.get(pid, {}).get("post", {})

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0,10, "BDNF Genotype Exercise Plan (12-week)", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0,8, f"Participant: {participant}", ln=True)
    pdf.cell(0,8, f"Genotype: {plan['genotype_label']}", ln=True)
    pdf.cell(0,8, f"Generated: {today}", ln=True)
    pdf.ln(4)

    # Include assessment summary table if present
    def write_assessment_table(pre, post):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0,8, "Assessment Summary (Pre vs Post)", ln=True)
        pdf.set_font("Helvetica", "", 11)
        keys = [
            ("MoCA","MoCA"),
            ("DigitSpan","Digit Span"),
            ("TMT_A","TMT-A (s)"),
            ("TMT_B","TMT-B (s)"),
            ("6MWT","6MWT (m)"),
            ("TUG","TUG (s)"),
            ("Handgrip","Handgrip (kg)"),
            ("BBS","BBS (0-56)")
        ]
        for k,label in keys:
            pre_v = pre.get(k,"-")
            post_v = post.get(k,"-")
            change = "-"
            try:
                if isinstance(pre_v,(int,float)) and isinstance(post_v,(int,float)):
                    change = round(post_v - pre_v,2)
            except:
                change = "-"
            pdf.cell(0,6, f"{label}: Pre: {pre_v} | Post: {post_v} | Change: {change}", ln=True)
        pdf.ln(4)

    if pre or post:
        write_assessment_table(pre, post)
    else:
        pdf.cell(0,8, "No assessments stored for this participant.", ln=True)

    # Add plan overview (first 4 weeks summary) to avoid excessively long PDFs
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0,8, "12-week Plan (overview)", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for w in plan["weeks"][:12]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0,6, f"Week {w['week']}", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for sess in w["sessions"]:
            txt = f"  {sess['day']}: {sess['type']} ({sess['duration_min']} min)"
            pdf.cell(0,6, txt, ln=True)
        pdf.ln(2)

    # Consent form page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0,10, "Participant Consent Form", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 11)
    consent_text = (
        "I confirm that I have received information about the exercise program. "
        "I understand the risks and benefits, and I consent to participate. "
        "I confirm that I have disclosed any medical conditions to the clinician."
    )
    pdf.multi_cell(0,6, consent_text)
    pdf.ln(8)
    pdf.cell(0,6, f"Participant name: {participant}", ln=True)
    pdf.cell(0,6, f"Date of birth: {dob}", ln=True)
    pdf.cell(0,6, f"Signature: ____________________________", ln=True)
    pdf.cell(0,6, f"Date: ____________________", ln=True)

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return (pdf_bytes, 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="bdnf_plan_and_consent.pdf"'
    })

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

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(debug=True)
