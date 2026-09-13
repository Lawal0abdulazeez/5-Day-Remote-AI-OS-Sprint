import re
from typing import Tuple, Dict


class PIIRedactor:
    """
    Redacts Personally Identifiable Information (PII) from resumes
    to enable unbiased, merit-based screening.
    """
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    LINKEDIN_PATTERN = re.compile(r'https?:\/\/(www\.)?linkedin\.com\/in\/[A-Za-z0-9_-]+', re.IGNORECASE)
    GITHUB_PATTERN = re.compile(r'https?:\/\/(www\.)?github\.com\/[A-Za-z0-9_-]+', re.IGNORECASE)
    URL_PATTERN = re.compile(r'https?:\/\/[^\s]+')
    
    # Generic name pattern on first few lines
    @classmethod
    def redact(cls, text: str, candidate_id: str) -> Tuple[str, Dict[str, str]]:
        redacted_text = text
        extracted_pii = {}
        
        # Redact emails
        emails = cls.EMAIL_PATTERN.findall(redacted_text)
        if emails:
            extracted_pii["email"] = emails[0]
            redacted_text = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted_text)
            
        # Redact phones
        phones = cls.PHONE_PATTERN.findall(redacted_text)
        if phones:
            extracted_pii["phone"] = "".join(phones[0]) if isinstance(phones[0], tuple) else phones[0]
            redacted_text = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted_text)
            
        # Redact social profiles
        redacted_text = cls.LINKEDIN_PATTERN.sub("[REDACTED_LINKEDIN]", redacted_text)
        redacted_text = cls.GITHUB_PATTERN.sub("[REDACTED_PORTFOLIO]", redacted_text)
        
        # Replace likely candidate header name (often line 1 or 2)
        lines = redacted_text.splitlines()
        clean_lines = []
        name_found = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not name_found and stripped and len(stripped.split()) in (2, 3, 4) and not any(kw in stripped.lower() for kw in ["resume", "curriculum", "engineer", "developer", "experience", "education"]):
                extracted_pii["name"] = stripped
                clean_lines.append(f"CANDIDATE-{candidate_id[:8].upper()}")
                name_found = True
            else:
                clean_lines.append(line)
                
        redacted_text = "\n".join(clean_lines)
        return redacted_text, extracted_pii
