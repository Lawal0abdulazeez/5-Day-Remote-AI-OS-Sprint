import os
import sys
import argparse
import json

# Ensure Quest root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.pipeline import ScreeningPipeline
from core.models import JobSpecification
from core.exporters.ats_exporter import ATSExporter


def main():
    parser = argparse.ArgumentParser(description="TalentOps AI OS Mini - CLI Candidate Evaluator")
    parser.add_argument("--resume", type=str, required=True, help="Path to resume file (PDF, DOCX, TXT)")
    parser.add_argument("--job", type=str, default="data/job_descriptions/senior_backend_engineer.json", help="Path to Job Description JSON")
    parser.add_argument("--anonymize", action="store_true", help="Enable PII redaction for blind screening")
    parser.add_argument("--export", type=str, choices=["console", "markdown", "greenhouse"], default="console", help="Export format")

    args = parser.parse_args()

    print("\n=======================================================")
    print("  TalentOps AI OS Mini: CLI Execution Interface")
    print("=======================================================\n")

    # 1. Load Job Specification
    if os.path.exists(args.job):
        with open(args.job, "r", encoding="utf-8") as f:
            job_spec = JobSpecification(**json.load(f))
    else:
        job_spec = JobSpecification()

    print(f"[*] Target Role: {job_spec.title}")
    print(f"[*] Analyzing Resume: {args.resume}")
    print(f"[*] Blind Screening: {args.anonymize}\n")

    # 2. Run Pipeline
    pipeline = ScreeningPipeline(data_dir="data")
    try:
        dossier = pipeline.process_candidate_file(
            file_path=args.resume,
            job_spec=job_spec,
            anonymize_pii=args.anonymize
        )
    except Exception as e:
        print(f"[ERROR] Pipeline execution failed: {e}")
        sys.exit(1)

    # 3. Display Results
    print(f"--- CANDIDATE EVIDENCE DOSSIER ---")
    print(f"Candidate: {dossier.candidate_name}")
    print(f"Overall Score: {dossier.overall_score}/100")
    print(f"Recommendation: {dossier.recommendation.value}")
    print(f"Latency: {dossier.processing_time_ms} ms")
    
    if dossier.security_audit.has_injection_risk:
        print(f"\n[!] SECURITY WARNING: Prompt injection attempt detected and neutralized!")

    print("\n[Criteria Breakdown]")
    for card in dossier.scorecards:
        print(f"  - {card.criterion_name}: {card.score} pts ({card.status.value})")
        if card.evidence_quotes:
            print(f"    Evidence: {card.evidence_quotes[0]}")

    print("\n[Key Strengths]")
    for s in dossier.strengths:
        print(f"  + {s}")

    print("\n[Identified Gaps]")
    for g in dossier.gaps_and_concerns:
        print(f"  - {g}")

    print("\n[Suggested Interview Probes]")
    for i, probe in enumerate(dossier.suggested_interview_probes, 1):
        print(f"  {i}. [{probe.category}] {probe.question}")

    if args.export == "markdown":
        md = ATSExporter.to_markdown_summary(dossier)
        out_file = f"data/dossiers/{dossier.dossier_id}_summary.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n[SUCCESS] Markdown summary exported to {out_file}")
    elif args.export == "greenhouse":
        gh = ATSExporter.to_greenhouse_payload(dossier)
        out_file = f"data/dossiers/{dossier.dossier_id}_greenhouse.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(gh, f, indent=2)
        print(f"\n[SUCCESS] Greenhouse ATS payload exported to {out_file}")

    print("\n=======================================================\n")


if __name__ == "__main__":
    main()
