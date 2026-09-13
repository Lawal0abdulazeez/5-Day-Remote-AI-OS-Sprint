# Day 2: System Architecture, Data Contracts & Design

---

## 1. End-to-End System Architecture

The **TalentOps AI OS Mini** is designed around clear separation of concerns, defensive validation, deterministic scoring, and human-in-the-loop (HITL) checkpoints:

```
                  ┌────────────────────────────────────────┐
                  │          Recruiter / Hiring Mgr        │
                  │        (Modern Web UI / Dashboard)     │
                  └───────────────┬────────────────────────┘
                                  │ HTTP / Multipart Upload
                                  ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Web Service                              │
│  - REST Endpoints (/api/screen, /api/dossiers, /api/approve, /api/export) │
│  - Request Validation, CORS, Static Asset Serving                         │
└─────────────────────────────────┬─────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    Orchestration Pipeline (`pipeline.py`)                 │
│  1. Ingestion & File Type Verification (PDF / DOCX / TXT)                 │
│  2. Structural Text Normalization & Layout Parsing                        │
│  3. Optional PII Redaction / Anonymization Layer                          │
│  4. Prompt Injection & Adversarial Sanitizer                              │
│  5. Criteria Extraction & Competency Alignment (LLM / Fallback)           │
│  6. Evidence Extraction & Direct Quote Grounding Verification             │
│  7. Red Flag, Green Flag & Gap Analyzer                                   │
│  8. Role-Specific Interview Probe Generator                               │
│  9. Multi-Dimensional Score Synthesis & Recommendation Formatter          │
└──────────────────┬──────────────────────┬─────────────────────────────────┘
                   │                      │
                   ▼                      ▼
┌───────────────────────────────┐  ┌────────────────────────────────────────┐
│     Pluggable LLM Adapter     │  │       Storage & Persistence Layer      │
│ - Mock Provider (Offline Fast)│  │ - JSON-backed Dossier Store            │
│ - OpenAI / Gemini / Anthropic │  │ - Audit Log Trace Store                │
│ - Automatic Retry & Fallback  │  │ - File System Artifact Cache           │
└───────────────────────────────┘  └────────────────────────────────────────┘
                                  │
                                  ▼
                   ┌───────────────────────────────┐
                   │    Human Approval Gateway     │
                   │ - Recruiter Sign-Off / Reject │
                   │ - Override Notes & Signatures │
                   │ - ATS Webhook / JSON Export   │
                   └───────────────────────────────┘
```

---

## 2. Input/Output Data Contracts & Schemas

### 2.1 Job Specification Schema (`JobSpecification`)
- `role_title`: str (e.g., "Senior Distributed Systems Engineer")
- `department`: str (e.g., "Core Infrastructure")
- `seniority_level`: str (e.g., "Senior / Staff")
- `required_skills`: List of competencies with minimum required years and importance weight (Mandatory / Preferred / Nice-to-have)
- `key_responsibilities`: List of expected core deliverables
- `minimum_years_experience`: int
- `educational_requirement`: Optional[str]
- `location_requirement`: str (e.g., "Remote (US/EU/Global)")

### 2.2 Candidate Ingestion Schema (`CandidateInput`)
- `candidate_id`: str (UUID)
- `raw_text`: str (Parsed resume text)
- `file_name`: str
- `file_type`: str ("pdf", "docx", "txt")
- `anonymize_pii`: bool

### 2.3 Evidence Scorecard Schema (`EvidenceScorecard`)
- `criterion_name`: str
- `weight`: float (0.0 to 1.0)
- `score`: float (0 to 100)
- `status`: Enum ("Exceeds", "Meets", "Partial", "Missing")
- `evidence_quotes`: List[str] (Exact quoted snippets from candidate document)
- `analysis_notes`: str

### 2.4 Comprehensive Evidence Dossier Schema (`CandidateDossier`)
- `dossier_id`: str (UUID)
- `candidate_name`: str (or "ANONYMIZED_CANDIDATE_xxxx" if PII redacted)
- `role_title`: str
- `overall_score`: float (0 to 100)
- `recommendation`: Enum ("Strong Advance", "Advance to Screen", "Hold / Review", "Respectful Reject")
- `scorecards`: List[EvidenceScorecard]
- `strengths`: List[str] (with citations)
- `gaps_and_concerns`: List[str] (with citations)
- `security_alerts`: List[str] (Prompt injection warnings or parsing anomalies)
- `suggested_interview_probes`: List[InterviewProbe] (Technical + Behavioral + Situational)
- `human_approval`: ApprovalStatus ("Pending", "Approved", "Rejected", "Manual Override")
- `recruiter_notes`: Optional[str]
- `timestamp`: str (ISO 8601)

---

## 3. Technology & Component Choices with Rationale

| Component | Technology | Rationale & Trade-offs |
| :--- | :--- | :--- |
| **Parsing Engine** | `pypdf` + `python-docx` + Regex normalizer | Pure Python, cross-platform, zero native C-library dependencies. Gracefully falls back to plain text extraction if multi-column layout is irregular. |
| **Orchestration** | Python FastAPI + Pydantic v2 | Industry-standard schema enforcement, automated OpenAPI documentation, high async throughput, and native validation errors. |
| **Model Adapter** | Multi-Provider Engine with Offline Mock Fallback | Guarantees 100% test reproducibility even when evaluators do not provide third-party API keys, while fully supporting live OpenAI/Gemini/Anthropic models when keys are supplied. |
| **Storage Layer** | Lightweight JSON/SQLite File Store | Zero external database server requirement. Preserves full audit history and dossiers locally across server restarts. |
| **User Interface** | Modern Vanilla HTML5/CSS/JavaScript | Instant zero-build startup (no `npm install` wait or node version mismatch for evaluators); responsive, dark-mode glassmorphism design with live scorecard gauges. |

---

## 4. Human Approval Points & Permission Boundaries

1. **Gate 1: Pre-Screening Sanitization**:
   - Recruiter can toggle **Anonymized Blind Screening** before running evaluation to strip names, photos, gender-identifying pronouns, and graduation years, curbing unconscious bias.
2. **Gate 2: Adversarial / Injection Isolation**:
   - Any prompt injection attempts in resumes are flagged and quarantined. The system alerts the recruiter: *"Adversarial input detected in Candidate Summary. LLM override blocked."*
3. **Gate 3: Explicit Recruiter Sign-Off**:
   - The AI OS never dispatches automated ATS status changes on its own.
   - The recruiter must review the evidence dossier, read cited quotes, add custom notes or override scoring, and explicitly click **Approve to Screen** or **Reject**.
4. **Gate 4: Audit Trail Immutability**:
   - Every approval, rejection, and score override is timestamped in an append-only audit trail with the operator's ID.

---

## 5. Evaluation Rubric & Pass/Fail Criteria

A candidate is evaluated across four core weighted pillars:

$$\text{Overall Score} = 0.35 \times \text{Core Skills} + 0.30 \times \text{Domain Experience} + 0.20 \times \text{Project Impact} + 0.15 \times \text{Role Alignment}$$

| Score Range | Category | Action |
| :--- | :--- | :--- |
| **85 – 100** | **Strong Advance** | Immediately schedule First-Round Technical Screen; generate deep probe questions. |
| **70 – 84** | **Advance to Screen** | Schedule Recruiter Screen; investigate identified gaps during call. |
| **50 – 69** | **Hold / Manual Review** | Route to Hiring Manager for secondary review or consider for adjacent/junior pool. |
| **0 – 49** | **Respectful Reject** | Queue respectful feedback email referencing unfulfilled requirements. |
