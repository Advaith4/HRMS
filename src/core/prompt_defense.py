"""
src/core/prompt_defense.py
Adversarial Prompt Injection Defense and XML Boundary Isolation Engine for TalentForge AI.
Safeguards LLM pipelines against direct instruction overrides, jailbreaks, delimiter escapes, and indirect prompt injections.
"""
import html
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("talentforge.security")

SECURITY_LOGS_DIR = Path("evidence/security")
PROMPT_INJECTION_AUDIT_FILE = SECURITY_LOGS_DIR / "prompt_injection_audit.jsonl"


class PromptDefenseEngine:
    """
    Defense system for LLM inputs providing XML boundary isolation,
    escape tag neutralization, and signature-based attack interception.
    """

    # High-risk adversarial injection signatures
    ATTACK_PATTERNS = [
        (re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|commands)\b", re.I), "INSTRUCTION_OVERRIDE", 1.0),
        (re.compile(r"\bdisregard\s+(?:all\s+)?(?:rules|guidelines|system|constraints|policies)\b", re.I), "RULE_DISREGARD", 0.95),
        (re.compile(r"\bsystem\s+prompt\s+override\b", re.I), "SYSTEM_OVERRIDE", 1.0),
        (re.compile(r"\byou\s+are\s+now\s+(?:DAN|jailbroken|unrestricted|an\s+unfiltered|in\s+developer\s+mode)\b", re.I), "JAILBREAK_PERSONA", 1.0),
        (re.compile(r"\bforget\s+everything\s+(?:you\s+know|previously\s+told)\b", re.I), "MEMORY_WIPE_ATTACK", 0.9),
        (re.compile(r"\b(?:reveal|print|show|output|leak|exfiltrate)\s+(?:your\s+)?(?:system\s+prompt|secret\s+instructions|hidden\s+rules)\b", re.I), "SYSTEM_PROMPT_EXTRACTION", 0.95),
        (re.compile(r"\bnew\s+system\s+instructions\s*:", re.I), "SYSTEM_INJECTION_PREFIX", 0.9),
        (re.compile(r"\bimportant\s*:\s*the\s+above\s+is\s+a\s+test,\s+instead\b", re.I), "TEST_OVERRIDE_ESCAPE", 0.85),
        (re.compile(r"\bact\s+as\s+(?:an?\s+)?unaligned|unconstrained\s+AI\b", re.I), "ALIGNMENT_BYPASS", 0.95),
        (re.compile(r"<\s*/\s*(?:candidate_resume|job_description|company_policy|user_input)\s*>", re.I), "XML_DELIMITER_ESCAPE", 1.0),
        (re.compile(r"\bdo\s+not\s+follow\s+any\s+(?:safety|hiring)\s+guidelines\b", re.I), "SAFETY_BYPASS", 0.9),
    ]

    @classmethod
    def sanitize_delimiters(cls, text: str, tag_name: str) -> str:
        """
        Prevents prompt boundary breakout by escaping closing and opening tags of the boundary XML.
        """
        if not text:
            return ""

        # Replace exact matching closing tags with escaped HTML entities
        escaped = re.sub(
            rf"<\s*/\s*{tag_name}\s*>",
            f"&lt;/{tag_name}&gt;",
            text,
            flags=re.IGNORECASE,
        )
        # Also neutralize opening tag spoofing
        escaped = re.sub(
            rf"<\s*{tag_name}\s*>",
            f"&lt;{tag_name}&gt;",
            escaped,
            flags=re.IGNORECASE,
        )
        return escaped

    @classmethod
    def scan_for_attacks(cls, text: str) -> Tuple[float, List[str], List[str]]:
        """
        Scans input for prompt injection signatures.
        Returns: (threat_score 0.0-1.0, list of attack types, list of matched patterns)
        """
        if not text:
            return 0.0, [], []

        max_score = 0.0
        detected_types = []
        matched_snippets = []

        for pattern, attack_type, score in cls.ATTACK_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                if score > max_score:
                    max_score = score
                if attack_type not in detected_types:
                    detected_types.append(attack_type)
                matched_snippets.extend(matches)

        return round(max_score, 2), detected_types, matched_snippets

    @classmethod
    def wrap_with_boundary(
        cls,
        untrusted_content: str,
        tag_name: str = "candidate_resume",
        neutralize_attacks: bool = True,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Encloses untrusted content into a rigid XML security boundary.
        Scans for prompt injection attacks and logs security intercepts.
        """
        if not untrusted_content:
            return {
                "wrapped_prompt": f"<{tag_name}>\n</{tag_name}>",
                "threat_score": 0.0,
                "is_attack": False,
                "classification": "SAFE",
                "detected_types": [],
            }

        threat_score, attack_types, matched_snippets = cls.scan_for_attacks(untrusted_content)
        is_attack = threat_score >= 0.75

        # Sanitize internal delimiter tags
        safe_content = cls.sanitize_delimiters(untrusted_content, tag_name)

        if is_attack and neutralize_attacks:
            # Neutralize detected attack phrases by neutralizing keywords
            for pattern, _, _ in cls.ATTACK_PATTERNS:
                safe_content = pattern.sub("[BLOCKED_INJECTION_ATTEMPT]", safe_content)

        # Rigid XML Envelope
        wrapped = (
            f"<{tag_name} secure_boundary=\"true\">\n"
            f"{safe_content.strip()}\n"
            f"</{tag_name}>"
        )

        classification = "ATTACK_BLOCKED" if is_attack else ("SUSPICIOUS" if threat_score > 0.3 else "SAFE")

        # Log security audit record
        if is_attack or threat_score > 0.0:
            cls.log_security_event(
                request_id=request_id or "sec-auto",
                tag_name=tag_name,
                threat_score=threat_score,
                classification=classification,
                detected_types=attack_types,
                snippets=matched_snippets,
            )

        return {
            "wrapped_prompt": wrapped,
            "threat_score": threat_score,
            "is_attack": is_attack,
            "classification": classification,
            "detected_types": attack_types,
            "sanitized_content": safe_content,
        }

    @classmethod
    def log_security_event(
        cls,
        request_id: str,
        tag_name: str,
        threat_score: float,
        classification: str,
        detected_types: List[str],
        snippets: List[str],
    ) -> Dict[str, Any]:
        """
        Appends structured security interception event to prompt_injection_audit.jsonl.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "boundary_tag": tag_name,
            "threat_score": threat_score,
            "classification": classification,
            "detected_types": detected_types,
            "matched_snippets_count": len(snippets),
        }

        try:
            SECURITY_LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(PROMPT_INJECTION_AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.warning("Failed to write to prompt injection audit log: %s", exc)

        logger.info("SECURITY_INTERCEPT: %s", json.dumps(entry))
        return entry

