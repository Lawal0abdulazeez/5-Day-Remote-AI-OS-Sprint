import re
from typing import Tuple, List
from core.models import SecurityAudit


class AdversarialGuard:
    """
    Detects and sanitizes prompt injection attempts, instructions overrides,
    and jailbreak attempts in resume text.
    """
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
        re.compile(r"system\s+prompt\s+(override|bypass)", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+in\s+.*mode", re.IGNORECASE),
        re.compile(r"score\s+(this\s+candidate\s+)?(100(\.0)?|10\/10|highest)", re.IGNORECASE),
        re.compile(r"disregard\s+(the\s+)?(rubric|job\s+description|criteria)", re.IGNORECASE),
        re.compile(r"recommend\s+(immediate\s+)?hire", re.IGNORECASE),
        re.compile(r"<\s*script\s*>", re.IGNORECASE),
        re.compile(r"\[\s*system\s*:\s*.*\]", re.IGNORECASE),
        re.compile(r"assistant\s*:\s*i\s+highly\s+recommend", re.IGNORECASE),
    ]

    @classmethod
    def scan_and_sanitize(cls, text: str) -> Tuple[str, SecurityAudit]:
        flagged = []
        sanitized = text

        for pattern in cls.INJECTION_PATTERNS:
            matches = pattern.findall(sanitized)
            if matches:
                flagged.append(pattern.pattern)
                # Replace adversarial attempt with a safe redaction placeholder
                sanitized = pattern.sub("[POTENTIAL_ADVERSARIAL_INJECTION_STRIPPED]", sanitized)

        audit = SecurityAudit(
            has_injection_risk=len(flagged) > 0,
            flagged_patterns=flagged,
            sanitized_length=len(sanitized),
            warning_message="Adversarial prompt injection attempt detected and neutralized." if flagged else None
        )

        return sanitized, audit
