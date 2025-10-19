# BDNF Genotype Exercise Planner (Render-ready)

A 12-week genotype-informed exercise prescription system with pre/post assessment tracking and PDF export.

## Deploy on Render
1. Push this folder to a GitHub repository (e.g., `bdnf-plan-app`).
2. Go to https://render.com → New → Web Service → Connect your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Done!

## Features
- Flask backend (Python 3.11)
- Frontend in static/ (HTML, CSS, JS)
- PDF generator with assessment summary + consent form
- Local JSON storage (no DB required)
- Admin editor: /admin?key=admin

Developed by: Assoc. Prof. Dr. Hazwani Ahmad Yusof @ Hanafi — IPPT, Universiti Sains Malaysia
