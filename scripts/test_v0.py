import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.pipeline import ScreeningPipeline
from core.models import JobSpecification

def main():
    print("=== TalentOps AI OS Mini: v0 Pipeline Verification ===")
    pipeline = ScreeningPipeline(data_dir="data")

    # Load job spec
    with open("data/job_descriptions/senior_backend_engineer.json", "r") as f:
        job_data = json.load(f)
    job_spec = JobSpecification(**job_data)

    print(f"\n1. Target Role: {job_spec.title} (Min {job_spec.minimum_years_experience} yrs)")

    # Test Golden Candidate
    print("\n--- Testing Golden Candidate (Alex Chen) ---")
    dossier = pipeline.process_candidate_file(
        file_path="data/sample_resumes/golden_hire_alex_chen.txt",
        job_spec=job_spec
    )
    print(f"Candidate: {dossier.candidate_name}")
    print(f"Overall Score: {dossier.overall_score}/100")
    print(f"Recommendation: {dossier.recommendation.value}")
    print(f"Processing Time: {dossier.processing_time_ms} ms")
    print(f"Injection Risk: {dossier.security_audit.has_injection_risk}")
    print(f"Top Strengths: {dossier.strengths[:2]}")

    # Test Adversarial Candidate
    print("\n--- Testing Adversarial Prompt Injection Candidate (Jordan Miller) ---")
    adv_dossier = pipeline.process_candidate_file(
        file_path="data/sample_resumes/prompt_injection_hacker.txt",
        job_spec=job_spec
    )
    print(f"Candidate: {adv_dossier.candidate_name}")
    print(f"Overall Score: {adv_dossier.overall_score}/100")
    print(f"Recommendation: {adv_dossier.recommendation.value}")
    print(f"Injection Risk Flagged: {adv_dossier.security_audit.has_injection_risk}")
    print(f"Flagged Patterns: {adv_dossier.security_audit.flagged_patterns}")
    print(f"Warning: {adv_dossier.security_audit.warning_message}")

    assert dossier.overall_score >= 85, "Golden candidate should score >= 85"
    assert adv_dossier.security_audit.has_injection_risk is True, "Security audit should flag injection"
    assert adv_dossier.overall_score < 70, "Injected score must NOT be 100!"

    print("\n[SUCCESS] v0 Pipeline verified end-to-end with security isolation!")

if __name__ == "__main__":
    main()
