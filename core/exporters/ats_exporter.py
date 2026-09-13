import os
import json
from typing import Dict, Any
from core.models import CandidateDossier, ApprovalStatus


class ATSExporter:
    """
    Second Tool Integration: Formats Candidate Dossiers into
    standard ATS schemas (Greenhouse/Lever compliant) and produces
    printable executive summaries.
    """

    @classmethod
    def to_greenhouse_payload(cls, dossier: CandidateDossier) -> Dict[str, Any]:
        """Maps dossier to standard Greenhouse Harvest API candidate & scorecard format."""
        status_map = {
            ApprovalStatus.APPROVED: "advance_to_technical_screen",
            ApprovalStatus.REJECTED: "rejected_does_not_meet_criteria",
            ApprovalStatus.MANUAL_OVERRIDE: "hiring_manager_review",
            ApprovalStatus.PENDING: "in_review"
        }

        attributes = [
            {
                "name": card.criterion_name,
                "type": "single_select",
                "value": card.status.value,
                "notes": f"Score: {card.score}/100. Evidence: {card.evidence_quotes[0] if card.evidence_quotes else 'None'}"
            }
            for card in dossier.scorecards
        ]

        payload = {
            "source": "TalentOps AI OS Mini",
            "candidate": {
                "name": dossier.candidate_name,
                "email": dossier.email or "unspecified@ats.local",
                "role": dossier.role_title,
                "anonymized": dossier.is_anonymized
            },
            "scorecard": {
                "overall_recommendation": dossier.recommendation.value,
                "overall_score": dossier.overall_score,
                "score_scale": "100_point_grounded_rubric",
                "key_strengths": dossier.strengths,
                "gaps_and_concerns": dossier.gaps_and_concerns,
                "custom_attributes": attributes,
                "security_flag": dossier.security_audit.has_injection_risk,
                "suggested_interview_probes": [
                    {"category": p.category, "question": p.question, "criteria": p.what_to_look_for}
                    for p in dossier.suggested_interview_probes
                ]
            },
            "human_approval": {
                "status": status_map.get(dossier.approval_status, "in_review"),
                "reviewed_by": dossier.reviewed_by or "Pending",
                "recruiter_notes": dossier.recruiter_notes or "Awaiting reviewer submission"
            },
            "timestamp": dossier.created_at
        }
        return payload

    @classmethod
    def to_markdown_summary(cls, dossier: CandidateDossier) -> str:
        """Generates an executive markdown dossier suitable for sharing in Slack/Notion."""
        md = []
        md.append(f"# Candidate Evidence Dossier: {dossier.candidate_name}")
        md.append(f"**Target Role**: {dossier.role_title} | **Date**: {dossier.created_at[:10]}")
        md.append(f"**Overall Score**: `{dossier.overall_score}/100` | **Recommendation**: `{dossier.recommendation.value}`")
        md.append(f"**Approval Status**: `{dossier.approval_status.value}` (Reviewed by: {dossier.reviewed_by or 'None'})\n")
        
        if dossier.security_audit.has_injection_risk:
            md.append("> ⚠️ **SECURITY ALERT**: Prompt injection attempt was detected in this candidate's submission and neutralized.\n")

        md.append("## 📊 Competency Scorecard")
        for card in dossier.scorecards:
            md.append(f"- **{card.criterion_name}** (`{card.status.value}` - {card.score} pts, wt: {int(card.weight*100)}%)")
            md.append(f"  - *Analysis*: {card.analysis}")
            if card.evidence_quotes:
                md.append(f"  - *Direct Evidence*: {card.evidence_quotes[0]}")

        md.append("\n## 🌟 Key Strengths")
        for s in dossier.strengths:
            md.append(f"- {s}")

        md.append("\n## ⚠️ Gaps & Potential Risks")
        for g in dossier.gaps_and_concerns:
            md.append(f"- {g}")

        md.append("\n## 🎯 Tailored Interview Probes")
        for i, probe in enumerate(dossier.suggested_interview_probes, 1):
            md.append(f"**{i}. [{probe.category}]** {probe.question}")
            md.append(f"   *Focus*: {probe.what_to_look_for}")

        if dossier.recruiter_notes:
            md.append(f"\n## ✍️ Recruiter Notes\n>{dossier.recruiter_notes}")

        return "\n".join(md)
