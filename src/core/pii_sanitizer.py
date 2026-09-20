"""
src/core/pii_sanitizer.py
High-Performance Regex-Based PII Sanitizer and Redactor for TalentForge AI.
Safeguards Personally Identifiable Information (PII) before LLM submission and structured logging.
"""
import re
from typing import Any, Dict, List, Union


class PIISanitizer:
    """
    Detects and redacts sensitive PII fields (Emails, Phone Numbers, SSNs, Credit Cards)
    from candidate resumes, recruiter notes, and audit logs.
    """

    # Compiled regex patterns for maximum throughput
    EMAIL_PATTERN = re.compile(
        r"\b([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b"
    )
    PHONE_PATTERN = re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    )
    SSN_PATTERN = re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    )
    CREDIT_CARD_PATTERN = re.compile(
        r"\b(?:\d[ -]*?){13,16}\b"
    )

    @classmethod
    def mask_email(cls, match: re.Match) -> str:
        """Mask email to format: j***@domain.com."""
        user, domain = match.group(1), match.group(2)
        if len(user) <= 1:
            masked_user = "*"
        else:
            masked_user = user[0] + "***"
        return f"{masked_user}@{domain}"

    @classmethod
    def mask_phone(cls, match: re.Match) -> str:
        """Mask phone number to format: +X-***-***-1234 or ***-***-1234."""
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 4:
            last4 = digits[-4:]
            return f"***-***-{last4}"
        return "[REDACTED_PHONE]"

    @classmethod
    def mask_ssn(cls, match: re.Match) -> str:
        """Mask SSN to format: ***-**-6789."""
        raw = match.group(0).strip()
        return f"***-**-{raw[-4:]}"

    @classmethod
    def mask_credit_card(cls, match: re.Match) -> str:
        """Mask credit card number to format: ****-****-****-1234."""
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) >= 4:
            return f"****-****-****-{digits[-4:]}"
        return "[REDACTED_CARD]"

    @classmethod
    def sanitize_text(
        cls,
        text: str,
        mask_emails: bool = True,
        mask_phones: bool = True,
        mask_ssns: bool = True,
        mask_cards: bool = True,
        mode: str = "partial",  # "partial" (e.g. j***@domain.com) or "full" (e.g. [REDACTED_EMAIL])
    ) -> str:
        """
        Sanitizes text by masking or redacting detected PII patterns.
        """
        if not text:
            return ""

        sanitized = text

        if mask_ssns:
            if mode == "full":
                sanitized = cls.SSN_PATTERN.sub("[REDACTED_SSN]", sanitized)
            else:
                sanitized = cls.SSN_PATTERN.sub(cls.mask_ssn, sanitized)

        if mask_cards:
            if mode == "full":
                sanitized = cls.CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", sanitized)
            else:
                sanitized = cls.CREDIT_CARD_PATTERN.sub(cls.mask_credit_card, sanitized)

        if mask_emails:
            if mode == "full":
                sanitized = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)
            else:
                sanitized = cls.EMAIL_PATTERN.sub(cls.mask_email, sanitized)

        if mask_phones:
            if mode == "full":
                sanitized = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)
            else:
                sanitized = cls.PHONE_PATTERN.sub(cls.mask_phone, sanitized)

        return sanitized

    @classmethod
    def sanitize_dict(
        cls,
        data: Dict[str, Any],
        sensitive_keys: Union[List[str], set] = ("password", "hashed_password", "token", "secret", "access_token"),
    ) -> Dict[str, Any]:
        """
        Recursively sanitizes dictionary keys and text values.
        """
        cleaned = {}
        for k, v in data.items():
            if k.lower() in sensitive_keys:
                cleaned[k] = "[REDACTED_SECRET]"
            elif isinstance(v, str):
                cleaned[k] = cls.sanitize_text(v)
            elif isinstance(v, dict):
                cleaned[k] = cls.sanitize_dict(v, sensitive_keys)
            elif isinstance(v, list):
                cleaned[k] = [
                    cls.sanitize_dict(item, sensitive_keys) if isinstance(item, dict)
                    else (cls.sanitize_text(item) if isinstance(item, str) else item)
                    for item in v
                ]
            else:
                cleaned[k] = v
        return cleaned

    @classmethod
    def detect_pii(cls, text: str) -> Dict[str, List[str]]:
        """
        Scans text and returns a dictionary of detected PII occurrences.
        """
        if not text:
            return {"emails": [], "phones": [], "ssns": [], "cards": []}

        return {
            "emails": cls.EMAIL_PATTERN.findall(text),
            "phones": cls.PHONE_PATTERN.findall(text),
            "ssns": cls.SSN_PATTERN.findall(text),
            "cards": cls.CREDIT_CARD_PATTERN.findall(text),
        }

