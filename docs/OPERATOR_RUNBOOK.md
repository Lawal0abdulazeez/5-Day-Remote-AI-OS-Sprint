# Operator Runbook & Setup Guide
## TalentOps AI OS: Non-Developer & Operator Manual

---

## 1. Three-Step Setup Guide (Quickstart)

The entire system is designed for zero-friction setup. You do **not** need a paid LLM API key, Docker, or Node.js to evaluate the complete operating system.

### Prerequisites
- Python 3.10+ installed ([python.org](https://www.python.org/downloads/))
- Git installed

### Step 1: Clone Repository
```bash
git clone https://github.com/Lawal0abdulazeez/5-Day-Remote-AI-OS-Sprint.git
cd 5-Day-Remote-AI-OS-Sprint
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch System
#### Option A: One-Click Launchers
- **Windows**: Double-click `run.bat`
- **macOS / Linux**: Run `./run.sh`

#### Option B: Terminal Command
```bash
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:8000`**

---

## 2. Operating the Web Interface

### 1. Ingesting & Evaluating Resumes
1. Select the **Target Role & Rubric** from the dropdown.
2. Either:
   - Click one of the four **One-Click Test Profiles** (`🌟 Golden Senior Hire`, `⚠️ Prompt Injection`, `🎓 Transitioner / Jr`, `📈 Keyword Stuffer`).
   - Or drag & drop any local **PDF**, **DOCX**, or **TXT** resume into the upload zone.
3. *(Optional)* Toggle **"Blind Screening (Redact PII)"** to anonymize candidate name, email, phone, and gender-identifying information for unbiased merit evaluation.
4. Click **"Run AI OS Evaluation"**. The candidate evidence dossier will generate in < 15 milliseconds.

### 2. Reviewing the Evidence Dossier
- **Score Circle**: Shows overall weighted score out of 100.
- **Security Alert**: If an adversarial prompt injection was attempted, a red banner displays the neutralized pattern.
- **Criteria Scorecard**: Lists each evaluation pillar with exact quoted excerpts from the applicant's resume.
- **Strengths & Gaps**: Bulleted breakdown of role alignment.
- **Interview Probes**: Suggested technical and behavioral questions generated for the interviewer.

### 3. Human Approval Gate
1. Review the generated dossier.
2. Enter any notes or specific interview guidance in the **Recruiter Notes** field.
3. Click **"✓ Approve for Screen"** to advance the candidate, or **"✕ Reject Candidate"** to flag for respectful rejection.
4. Click **"Export ATS (JSON)"** to download the standard Greenhouse Harvest API payload, or **"Download Summary"** for Markdown.

### 4. Running the 10-Test Case Benchmark
1. Navigate to the **"10-Test Benchmark"** tab in the top navigation bar.
2. Click **"▶ Run Full Test Benchmark"**.
3. Watch the real-time execution matrix evaluate all 10 profiles, measure latencies, verify injection defenses, and confirm pass/fail statuses.

### 5. Inspecting Audit Logs
- Navigate to the **"Audit Logs"** tab to view the append-only event trail of all dossier creations, recruiter approvals, score overrides, and neutralized injection attempts.

---

## 3. Command-Line Interface (CLI) Manual

For headless execution or batch processing scripts:

```bash
# Evaluate a single candidate resume
python scripts/run_cli.py --resume data/sample_resumes/golden_hire_alex_chen.txt

# Run in Blind Screening mode with Greenhouse ATS export
python scripts/run_cli.py --resume data/sample_resumes/golden_hire_alex_chen.txt --anonymize --export greenhouse

# Run with custom Job Description
python scripts/run_cli.py --resume data/sample_resumes/golden_hire_alex_chen.txt --job data/job_descriptions/senior_backend_engineer.json
```

---

## 4. Troubleshooting & Maintenance

| Issue / Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| `Address already in use (Port 8000)` | Another process is using port 8000 | Set `PORT=8080` in `.env` or run `python -m uvicorn web.app:app --port 8080`. |
| `Document contains no parseable text` | PDF contains only scanned bitmap images without embedded text | Run external OCR or convert image to text before ingestion. |
| `ModuleNotFoundError: No module named 'core'` | Python running without workspace root in sys.path | Run scripts from repository root, e.g., `python -m pytest tests/` or use `run.bat`. |

---

## 5. Live Cloud Deployment

To deploy live on Render, Railway, or Heroku:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python -m uvicorn web.app:app --host 0.0.0.0 --port $PORT`
