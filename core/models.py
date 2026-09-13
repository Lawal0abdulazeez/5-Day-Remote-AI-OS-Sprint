from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    EXCEEDS = "Exceeds"
    MEETS = "Meets"
    PARTIAL = "Partial"
    MISSING = "Missing"


class RecommendationCategory(str, Enum):
    STRONG_ADVANCE = "Strong Advance"
    ADVANCE = "Advance to Screen"
    HOLD_REVIEW = "Hold / Manual Review"
    RESPECTFUL_REJECT = "Respectful Reject"


class ApprovalStatus(str, Enum):
    PENDING = "Pending Review"
    APPROVED = "Approved for Screen"
    REJECTED = "Rejected"
    MANUAL_OVERRIDE = "Manual Override"


class RequirementCriterion(BaseModel):
    name: str
    weight: float = Field(default=0.25, ge=0.0, le=1.0)
    mandatory: bool = True
    description: str


class JobSpecification(BaseModel):
    id: str = "job-001"
    title: str = "Senior Backend Engineer"
    department: str = "Core Engineering"
    seniority: str = "Senior"
    minimum_years_experience: int = 5
    required_skills: List[str] = Field(default_factory=lambda: ["Python", "Distributed Systems", "SQL/PostgreSQL", "Docker/Kubernetes"])
    preferred_skills: List[str] = Field(default_factory=lambda: ["FastAPI", "Kafka", "AWS/GCP", "System Design"])
    criteria: List[RequirementCriterion] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None


class CandidateInput(BaseModel):
    candidate_id: str
    file_name: str
    raw_text: str
    anonymize_pii: bool = False
    job_id: str = "job-001"


class EvidenceScorecard(BaseModel):
    criterion_name: str
    weight: float
    score: float = Field(ge=0.0, le=100.0)
    status: MatchStatus
    evidence_quotes: List[str] = Field(default_factory=list)
    analysis: str


class InterviewProbe(BaseModel):
    category: str  # "Technical", "Behavioral", "System Design", "Verification"
    question: str
    what_to_look_for: str


class SecurityAudit(BaseModel):
    has_injection_risk: bool = False
    flagged_patterns: List[str] = Field(default_factory=list)
    sanitized_length: int = 0
    warning_message: Optional[str] = None


class CandidateDossier(BaseModel):
    dossier_id: str
    candidate_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role_title: str
    job_id: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Quantitative Scores
    overall_score: float = Field(ge=0.0, le=100.0)
    recommendation: RecommendationCategory
    
    # Detailed Evidence
    scorecards: List[EvidenceScorecard] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    gaps_and_concerns: List[str] = Field(default_factory=list)
    
    # Tailored Next Steps
    suggested_interview_probes: List[InterviewProbe] = Field(default_factory=list)
    
    # Safety & Anonymization
    is_anonymized: bool = False
    security_audit: SecurityAudit = Field(default_factory=SecurityAudit)
    
    # Human Approval Gate
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    recruiter_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    
    # Parsed Profile Highlights
    years_experience_detected: Optional[float] = None
    top_skills_detected: List[str] = Field(default_factory=list)
    companies_or_projects: List[str] = Field(default_factory=list)
    
    # Execution Metadata
    processing_time_ms: float = 0.0
    llm_provider: str = "mock"


class ApprovalAction(BaseModel):
    dossier_id: str
    action: str  # "approve", "reject", "override"
    recruiter_name: str = "Talent Lead"
    notes: Optional[str] = None
    overridden_score: Optional[float] = None
