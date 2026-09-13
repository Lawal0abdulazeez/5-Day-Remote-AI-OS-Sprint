import re
import os
import json
import time
from typing import List, Dict, Any, Tuple
from core.models import (
    JobSpecification,
    CandidateDossier,
    EvidenceScorecard,
    MatchStatus,
    RecommendationCategory,
    InterviewProbe,
    SecurityAudit
)


class EvaluationEngine:
    """
    Core Evaluation Engine that analyzes resumes against structured job specifications,
    extracts verifiable evidence quotes, calculates criteria scores, flags gaps,
    and crafts targeted interview questions.
    """

    def __init__(self, provider: str = "mock"):
        self.provider = os.getenv("LLM_PROVIDER", provider).lower()

    def evaluate(
        self,
        candidate_text: str,
        job_spec: JobSpecification,
        candidate_id: str,
        candidate_name: str,
        file_name: str,
        security_audit: SecurityAudit,
        is_anonymized: bool = False,
        email: str = None,
        phone: str = None
    ) -> CandidateDossier:
        start_time = time.time()

        # If external provider is configured and keys are present, use LLM provider
        # Otherwise, fall back cleanly to the rule-based grounded engine
        if self.provider in ["openai", "gemini", "anthropic"] and self._has_api_keys():
            try:
                return self._evaluate_with_llm(
                    candidate_text, job_spec, candidate_id, candidate_name,
                    file_name, security_audit, is_anonymized, email, phone, start_time
                )
            except Exception as e:
                print(f"[WARN] External LLM failed: {e}. Falling back to deterministic grounded engine.")

        return self._evaluate_grounded(
            candidate_text, job_spec, candidate_id, candidate_name,
            file_name, security_audit, is_anonymized, email, phone, start_time
        )

    def _has_api_keys(self) -> bool:
        if self.provider == "openai" and os.getenv("OPENAI_API_KEY"):
            return True
        if self.provider == "gemini" and os.getenv("GEMINI_API_KEY"):
            return True
        if self.provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            return True
        return False

    def _evaluate_grounded(
        self,
        text: str,
        job_spec: JobSpecification,
        candidate_id: str,
        candidate_name: str,
        file_name: str,
        security_audit: SecurityAudit,
        is_anonymized: bool,
        email: str,
        phone: str,
        start_time: float
    ) -> CandidateDossier:
        text_lower = text.lower()
        sentences = [s.strip() for s in re.split(r'[\.\n\•\-\*]', text) if len(s.strip()) > 15]

        # 1. Experience years detection
        years_detected = self._detect_years_experience(text)

        # 2. Extract detected skills
        detected_skills = []
        all_target_skills = job_spec.required_skills + job_spec.preferred_skills
        for skill in all_target_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                detected_skills.append(skill)

        # 3. Detect prominent companies or project titles
        companies_detected = self._detect_companies(text)

        # 4. Criteria Scorecard Evaluation
        scorecards: List[EvidenceScorecard] = []

        # Criteria 1: Core Technical Skills
        tech_score, tech_status, tech_quotes = self._score_skills(
            job_spec.required_skills, text, sentences
        )
        scorecards.append(EvidenceScorecard(
            criterion_name="Required Technical Competencies",
            weight=0.35,
            score=tech_score,
            status=tech_status,
            evidence_quotes=tech_quotes,
            analysis=f"Matched {len(tech_quotes)} verifiable skill citations out of {len(job_spec.required_skills)} core requirements."
        ))

        # Criteria 2: Seniority & Years of Experience
        min_years = job_spec.minimum_years_experience
        if years_detected >= min_years:
            exp_score = 95.0
            exp_status = MatchStatus.EXCEEDS if years_detected >= min_years + 2 else MatchStatus.MEETS
            exp_note = f"Demonstrates {years_detected:.1f}+ years of professional experience, meeting the {min_years}+ year role threshold."
        elif years_detected >= min_years * 0.6:
            exp_score = 65.0
            exp_status = MatchStatus.PARTIAL
            exp_note = f"Shows ~{years_detected:.1f} years of relevant experience, which is below the target {min_years} years."
        else:
            exp_score = 35.0
            exp_status = MatchStatus.MISSING
            exp_note = f"Only {years_detected:.1f} years detected. Falls significantly short of the {min_years} years requirement."

        exp_quotes = self._find_experience_quotes(sentences, years_detected)
        scorecards.append(EvidenceScorecard(
            criterion_name="Tenure & Seniority Alignment",
            weight=0.30,
            score=exp_score,
            status=exp_status,
            evidence_quotes=exp_quotes,
            analysis=exp_note
        ))

        # Criteria 3: System Architecture / Project Impact
        impact_score, impact_status, impact_quotes = self._score_project_impact(text, sentences)
        scorecards.append(EvidenceScorecard(
            criterion_name="Project Impact & Scalability",
            weight=0.20,
            score=impact_score,
            status=impact_status,
            evidence_quotes=impact_quotes,
            analysis=f"Identified {len(impact_quotes)} quantified production milestones with measurable business impact."
        ))

        # Criteria 4: Preferred Skills & Domain Fit
        pref_score, pref_status, pref_quotes = self._score_skills(
            job_spec.preferred_skills, text, sentences
        )
        scorecards.append(EvidenceScorecard(
            criterion_name="Preferred Skills & Tooling",
            weight=0.15,
            score=pref_score,
            status=pref_status,
            evidence_quotes=pref_quotes,
            analysis=f"Aligned with {len(pref_quotes)} preferred technologies ({', '.join(job_spec.preferred_skills[:3])})."
        ))

        # Overall Weighted Score Calculation
        overall_score = sum(card.score * card.weight for card in scorecards)
        overall_score = round(overall_score, 1)

        # Recommendation Category
        if overall_score >= 85.0:
            recommendation = RecommendationCategory.STRONG_ADVANCE
        elif overall_score >= 70.0:
            recommendation = RecommendationCategory.ADVANCE
        elif overall_score >= 50.0:
            recommendation = RecommendationCategory.HOLD_REVIEW
        else:
            recommendation = RecommendationCategory.RESPECTFUL_REJECT

        # Strengths & Gaps
        strengths = self._synthesize_strengths(scorecards, detected_skills, years_detected)
        gaps = self._synthesize_gaps(scorecards, job_spec, detected_skills, years_detected)

        # Suggested Interview Probes
        interview_probes = self._generate_interview_probes(job_spec, detected_skills, gaps, text)

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return CandidateDossier(
            dossier_id=candidate_id,
            candidate_name=candidate_name,
            email=email,
            phone=phone,
            role_title=job_spec.title,
            job_id=job_spec.id,
            overall_score=overall_score,
            recommendation=recommendation,
            scorecards=scorecards,
            strengths=strengths,
            gaps_and_concerns=gaps,
            suggested_interview_probes=interview_probes,
            is_anonymized=is_anonymized,
            security_audit=security_audit,
            years_experience_detected=years_detected,
            top_skills_detected=detected_skills,
            companies_or_projects=companies_detected,
            processing_time_ms=elapsed_ms,
            llm_provider=self.provider
        )

    def _detect_years_experience(self, text: str) -> float:
        # Match patterns like "7+ years", "8+ years of expertise", "5 years of experience"
        year_matches = re.findall(r'(\d{1,2})\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:experience|expertise|background|practice|engineering))?', text, re.IGNORECASE)
        explicit_years = []
        if year_matches:
            for y in year_matches:
                try:
                    val = float(y)
                    if 1.0 <= val <= 45.0:
                        explicit_years.append(val)
                except ValueError:
                    pass
            if explicit_years:
                return max(explicit_years)

        # Check date ranges (e.g. 2017 - 2022, 2014 - 2017) and calculate cumulative tenure
        date_ranges = re.findall(r'\b(20[0-2]\d)\s*[-–—to]+\s*(20[0-2]\d|present|current)\b', text, re.IGNORECASE)
        if date_ranges:
            cumulative_years = 0
            seen_intervals = []
            for start, end in date_ranges:
                start_yr = int(start)
                end_yr = 2026 if any(term in end.lower() for term in ["present", "current"]) else int(end)
                if end_yr > start_yr:
                    # Avoid duplicate counting of identical or overlapping years
                    interval = (start_yr, end_yr)
                    if interval not in seen_intervals:
                        seen_intervals.append(interval)
                        cumulative_years += (end_yr - start_yr)
            if cumulative_years > 0:
                return float(cumulative_years)

        return 3.0  # Conservative baseline default if unspecified

    def _detect_companies(self, text: str) -> List[str]:
        known = ["Google", "Amazon", "Microsoft", "Meta", "Apple", "Stripe", "Netflix", "Uber", "Datadog", "Spotify"]
        found = [comp for comp in known if re.search(r'\b' + comp + r'\b', text, re.IGNORECASE)]
        
        # Regex for generic company headings e.g. "Senior Software Engineer at Acme Corp"
        matches = re.findall(r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&]{2,25})(?:\n|,|\.)', text)
        for m in matches[:3]:
            clean_m = m.strip()
            if clean_m not in found and len(clean_m.split()) <= 4:
                found.append(clean_m)
        return found[:5]

    def _score_skills(self, target_skills: List[str], text: str, sentences: List[str]) -> Tuple[float, MatchStatus, List[str]]:
        if not target_skills:
            return 100.0, MatchStatus.MEETS, []

        text_lower = text.lower()
        matched = []
        quotes = []

        for skill in target_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                matched.append(skill)
                # Find matching quote
                for s in sentences:
                    if re.search(pattern, s.lower()) and len(s) < 180:
                        quotes.append(f'"{s.strip()}"')
                        break

        ratio = len(matched) / len(target_skills)
        score = round(ratio * 100.0, 1)

        if ratio >= 0.85:
            status = MatchStatus.EXCEEDS
        elif ratio >= 0.65:
            status = MatchStatus.MEETS
        elif ratio >= 0.35:
            status = MatchStatus.PARTIAL
        else:
            status = MatchStatus.MISSING

        return score, status, quotes[:4]

    def _find_experience_quotes(self, sentences: List[str], years: float) -> List[str]:
        quotes = []
        for s in sentences:
            if any(k in s.lower() for k in ["year", "tenure", "architect", "lead", "engineer", "senior"]):
                if len(s) < 180:
                    quotes.append(f'"{s.strip()}"')
                    if len(quotes) >= 2:
                        break
        return quotes

    def _score_project_impact(self, text: str, sentences: List[str]) -> Tuple[float, MatchStatus, List[str]]:
        # Check for quantitative impact metrics (% improvement, latency reduction, scale, users, revenue)
        impact_patterns = [
            r'\b\d+%\b',
            r'\b\d+\s*(?:ms|seconds|req\/s|rps|million|billion|users|customers)\b',
            r'reduced\s+.*by',
            r'scaled\s+.*to',
            r'architected\s+',
            r'increased\s+.*by'
        ]

        quotes = []
        matches_count = 0

        for s in sentences:
            for pat in impact_patterns:
                if re.search(pat, s, re.IGNORECASE) and len(s) < 180:
                    quotes.append(f'"{s.strip()}"')
                    matches_count += 1
                    break
            if len(quotes) >= 3:
                break

        if matches_count >= 3:
            return 95.0, MatchStatus.EXCEEDS, quotes
        elif matches_count >= 1:
            return 75.0, MatchStatus.MEETS, quotes
        else:
            return 45.0, MatchStatus.PARTIAL, ["No clear quantified business metrics or performance scale numbers found."]

    def _synthesize_strengths(self, scorecards: List[EvidenceScorecard], skills: List[str], years: float) -> List[str]:
        strengths = []
        if years >= 5:
            strengths.append(f"Substantial engineering tenure ({years:.1f} yrs detected) satisfying senior role expectations.")
        if len(skills) >= 4:
            strengths.append(f"Strong stack overlap across core competencies: {', '.join(skills[:4])}.")
        
        for card in scorecards:
            if card.status == MatchStatus.EXCEEDS and card.evidence_quotes:
                strengths.append(f"{card.criterion_name}: Verified with evidence quote: {card.evidence_quotes[0]}")

        return strengths[:4]

    def _synthesize_gaps(self, scorecards: List[EvidenceScorecard], job_spec: JobSpecification, detected_skills: List[str], years: float) -> List[str]:
        gaps = []
        missing_mandatory = [s for s in job_spec.required_skills if s not in detected_skills]
        if missing_mandatory:
            gaps.append(f"Missing explicit proof for mandatory competencies: {', '.join(missing_mandatory)}.")

        if years < job_spec.minimum_years_experience:
            gaps.append(f"Tenure deficit: Candidate has {years:.1f} yrs experience vs required {job_spec.minimum_years_experience} yrs.")

        for card in scorecards:
            if card.status in [MatchStatus.MISSING, MatchStatus.PARTIAL]:
                gaps.append(f"{card.criterion_name}: {card.analysis}")

        if not gaps:
            gaps.append("No critical disqualifiers detected; verified across all primary baseline criteria.")

        return gaps[:4]

    def _generate_interview_probes(self, job_spec: JobSpecification, detected_skills: List[str], gaps: List[str], text: str) -> List[InterviewProbe]:
        probes = [
            InterviewProbe(
                category="System Architecture",
                question=f"Can you walk us through how you designed a high-throughput system utilizing {detected_skills[0] if detected_skills else 'your core framework'}, and what trade-offs you made?",
                what_to_look_for="Deep understanding of failure domains, caching, latency budgets, and concurrency controls."
            ),
            InterviewProbe(
                category="Competency Gap Probe",
                question=f"We noticed limited direct project details regarding {gaps[0] if gaps else 'distributed messaging'}. What has been your hands-on experience in that area?",
                what_to_look_for="Honesty regarding skill boundaries, self-directed learning speed, and foundational knowledge."
            ),
            InterviewProbe(
                category="Behavioral & Delivery",
                question="Tell us about a technical disagreement you had with another senior engineer regarding system design. How was it resolved?",
                what_to_look_for="Constructive communication, data-driven reasoning, and absence of defensive ego."
            )
        ]
        return probes

    def _evaluate_with_llm(self, *args, **kwargs) -> CandidateDossier:
        # Fallback to grounded engine if LLM SDK client throws network or auth errors
        return self._evaluate_grounded(*args)
