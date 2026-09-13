import uuid
import os
from typing import Optional, Dict, Any
from core.models import JobSpecification, CandidateDossier
from core.parsers.resume_parser import ResumeParser, DocumentParsingError
from core.evaluators.adversarial_guard import AdversarialGuard
from core.redactor import PIIRedactor
from core.evaluators.evaluator_engine import EvaluationEngine
from core.storage import StorageManager


class ScreeningPipeline:
    """
    End-to-End Orchestrator executing the Candidate Screener & Evidence Dossier flow:
    Parser -> Adversarial Quarantine -> Optional PII Redaction -> Grounded Evaluation -> Storage.
    """

    def __init__(self, data_dir: str = "data"):
        self.storage = StorageManager(data_dir=data_dir)
        self.evaluator = EvaluationEngine()

    def process_candidate_file(
        self,
        file_path: str,
        job_spec: Optional[JobSpecification] = None,
        candidate_name: Optional[str] = None,
        anonymize_pii: bool = False
    ) -> CandidateDossier:
        file_name = os.path.basename(file_path)
        raw_text = ResumeParser.parse_file(file_path)
        return self.process_candidate_text(
            raw_text=raw_text,
            file_name=file_name,
            job_spec=job_spec,
            candidate_name=candidate_name,
            anonymize_pii=anonymize_pii
        )

    def process_candidate_text(
        self,
        raw_text: str,
        file_name: str = "pasted_resume.txt",
        job_spec: Optional[JobSpecification] = None,
        candidate_name: Optional[str] = None,
        anonymize_pii: bool = False
    ) -> CandidateDossier:
        if job_spec is None:
            job_spec = JobSpecification()

        candidate_id = str(uuid.uuid4())

        # Step 1: Security Scan for Adversarial Prompt Injections
        clean_text, security_audit = AdversarialGuard.scan_and_sanitize(raw_text)

        # Step 2: Optional PII Redaction for Unbiased Screening
        extracted_pii = {}
        if anonymize_pii:
            clean_text, extracted_pii = PIIRedactor.redact(clean_text, candidate_id)
            effective_name = f"Candidate #{candidate_id[:6].upper()}"
            email = None
            phone = None
        else:
            # Detect name from first line if not provided
            if not candidate_name:
                first_lines = [l.strip() for l in clean_text.splitlines() if l.strip()]
                candidate_name = first_lines[0] if first_lines else "Unknown Candidate"
            effective_name = candidate_name
            email = None
            phone = None

        # Step 3: Core Evaluation & Grounded Evidence Extraction
        dossier = self.evaluator.evaluate(
            candidate_text=clean_text,
            job_spec=job_spec,
            candidate_id=candidate_id,
            candidate_name=effective_name,
            file_name=file_name,
            security_audit=security_audit,
            is_anonymized=anonymize_pii,
            email=email,
            phone=phone
        )

        # Step 4: Durable Persistence
        self.storage.save_dossier(dossier)

        return dossier
