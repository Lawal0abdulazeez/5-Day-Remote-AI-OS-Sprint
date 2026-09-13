import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from core.models import CandidateDossier, ApprovalStatus


class StorageManager:
    """
    Lightweight, durable JSON file-backed storage manager for
    candidate dossiers, recruiter approvals, and audit trails.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.dossiers_dir = os.path.join(data_dir, "dossiers")
        self.audit_log_file = os.path.join(data_dir, "audit_log.jsonl")
        
        os.makedirs(self.dossiers_dir, exist_ok=True)
        if not os.path.exists(self.audit_log_file):
            with open(self.audit_log_file, "w", encoding="utf-8") as f:
                pass

    def save_dossier(self, dossier: CandidateDossier) -> str:
        file_path = os.path.join(self.dossiers_dir, f"{dossier.dossier_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(dossier.model_dump_json(indent=2))
        
        self.log_audit_event(
            event_type="DOSSIER_CREATED",
            dossier_id=dossier.dossier_id,
            details={
                "candidate": dossier.candidate_name,
                "role": dossier.role_title,
                "score": dossier.overall_score,
                "recommendation": dossier.recommendation.value,
                "injection_detected": dossier.security_audit.has_injection_risk
            }
        )
        return file_path

    def get_dossier(self, dossier_id: str) -> Optional[CandidateDossier]:
        file_path = os.path.join(self.dossiers_dir, f"{dossier_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return CandidateDossier(**data)

    def list_dossiers(self) -> List[Dict[str, Any]]:
        dossiers = []
        if not os.path.exists(self.dossiers_dir):
            return dossiers

        for fname in os.listdir(self.dossiers_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.dossiers_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        dossiers.append({
                            "dossier_id": data.get("dossier_id"),
                            "candidate_name": data.get("candidate_name"),
                            "role_title": data.get("role_title"),
                            "overall_score": data.get("overall_score"),
                            "recommendation": data.get("recommendation"),
                            "approval_status": data.get("approval_status"),
                            "created_at": data.get("created_at"),
                            "has_injection_risk": data.get("security_audit", {}).get("has_injection_risk", False),
                            "processing_time_ms": data.get("processing_time_ms", 0.0)
                        })
                except Exception:
                    continue

        # Sort newest first
        dossiers.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return dossiers

    def update_approval(
        self,
        dossier_id: str,
        action: str,
        recruiter_name: str,
        notes: Optional[str] = None,
        overridden_score: Optional[float] = None
    ) -> Optional[CandidateDossier]:
        dossier = self.get_dossier(dossier_id)
        if not dossier:
            return None

        if action == "approve":
            dossier.approval_status = ApprovalStatus.APPROVED
        elif action == "reject":
            dossier.approval_status = ApprovalStatus.REJECTED
        elif action == "override":
            dossier.approval_status = ApprovalStatus.MANUAL_OVERRIDE
            if overridden_score is not None:
                dossier.overall_score = overridden_score

        dossier.reviewed_by = recruiter_name
        dossier.recruiter_notes = notes
        dossier.reviewed_at = datetime.utcnow().isoformat()

        self.save_dossier(dossier)
        self.log_audit_event(
            event_type=f"APPROVAL_{action.upper()}",
            dossier_id=dossier_id,
            details={
                "recruiter": recruiter_name,
                "notes": notes,
                "new_status": dossier.approval_status.value
            }
        )
        return dossier

    def log_audit_event(self, event_type: str, dossier_id: str, details: Dict[str, Any]):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "dossier_id": dossier_id,
            "details": details
        }
        with open(self.audit_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
