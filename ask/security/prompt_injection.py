from __future__ import annotations

import re
from dataclasses import dataclass, field

_KNOWN_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r'(?i)(?:ignore|disregard|forget|skip|bypass|never\s*mind|drop)\s+(?:all\s+|any\s+)?(?:above|previous|prior|the\s+above|given|prior|former|earlier|initial|instructions)'),
    re.compile(r'(?i)you\s+(?:are\s+(?:now|not\s+)?|must\s+)?(?:an?\s+)?(?:ChatGPT|AI|assistant|model|GPT|hacker|DAN)'),
    re.compile(r'(?i)(?:new\s+)?(?:system\s+)?(?:prompt|instructions?)\s*:'),
    re.compile(r'(?i)(?:reset|clear|overwrite|override|change|modify|alter|update)\s+(?:the\s+|your\s+|its\s+)?(?:system\s+)?(?:prompt|instructions?|behavior|personality|persona|role|rules)'),
    re.compile(r'(?i)(?:do\s+(?:not\s+)?|must\s+(?:not\s+)?|can\s+(?:not\s+)?|should\s+(?:not\s+)?|will\s+(?:not\s+)?)\s*(?:follow|obey|listen|heed|adhere)\s+(?:to\s+)?(?:the\s+|these\s+|those\s+|any\s+|all\s+)?(?:above|prior|previous|given|instructions?|rules?|commands?|constraints?|guidelines?)'),
    re.compile(r'(?i)you\s+must\s+(?:not\s+)?(?:output|respond|reply|answer)\s+in'),
    re.compile(r'(?i)act\s+as\s+(?:if\s+you\s+are|an?\s+|a\s+)'),
    re.compile(r'(?i)omit\w*\s+(?:the\s+)?(?:above|system|initial|given|prior)\s+(?:instructions?|prompt|rules?)'),
    re.compile(r'(?i)(?:start|begin|reply|respond)\s+(?:with|by|using)\s+(?:the\s+)?(?:word|phrase|text|string|letter)'),
    re.compile(r'(?i)print\s+(?:the\s+)?(?:above|system|initial|prompt|rules?)'),
    re.compile(r'(?i)(?:show|display|reveal|output|leak|expose|dump|extract|tell|give)\s+(?:\w+\s+){0,3}(?:the\s+|me\s+)?(?:system|initial|above|full|entire|your|original)\s+(?:prompt|instructions?|messages?|content|text|rules?)'),
    re.compile(r'(?i)(?:ignore|skip|bypass|circumvent)\s+(?:safety|security|guardrails?|filter|restrictions?|rules|alignment|safeguards?)'),
    re.compile(r'(?i)(?:tell\s+me|write|output|print|show)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?)'),
    re.compile(r'(?i)say\s+(?:"[^"]*"|\'[^\']*\').*and\s+(?:nothing|that\'?s?)\s+(?:else|all)'),
    re.compile(r'(?i)(?:DAN|do\s+anything\s+now|jailbreak|prompt\s+inject|prompt\s+leak)'),
    re.compile(r'(?i)you\s+(?:will|must|shall)\s+now\s+(?:act|behave|respond|output|follow)'),
    re.compile(r'(?i)(?:pretend|imagine|roleplay|role-play)\s+(?:that\s+)?(?:you\s+are|you\s+have|as\s+if|being)'),
    re.compile(r'(?i)(?:you\s+(?:are\s+)?)?\bfree\b\s*(?:\w+\s*){0,8}(?:from\s+)?(?:rules?|restrictions?|constraints?|limitations?|protocols?)'),
    re.compile(r'(?i)\bno\s+(?:rules?|limits?|restrictions?|boundaries?|filtering?|guardrails?)\b'),
    re.compile(r'(?i)(?:answer|reply|respond)\s+(?:in\s+)?(?:a\s+)?(?:way\s+that\s+)?bypass'),
    re.compile(r'(?i)(?:you\s+don\'?t\s+(?:have\s+to|need\s+to)\s+(?:follow|obey|adhere))'),
    re.compile(r'(?i)(?:output|return|give)\s+(?:the\s+)?(?:raw|exact|full|complete|original|unfiltered)\s+(?:text|content|response|message|output|version)'),
    re.compile(r'(?i)i\s+(?:want|need|require|demand)\s+you\s+to\s+(?:forget|ignore|disregard|bypass)\s+'),
    re.compile(r'(?i)(?:repeat|say|echo|mirror)\s+(?:"[^"]*"|\'[^\']*\')'),
    re.compile(r'(?i)(?:translate|convert|encode)\s+(?:to|into)\s+(?:leet|l33t|base64|rot13|morse)'),
    re.compile(r'(?i)\bunfiltered\b|\buncensored\b|\bunconstrained\b'),
    re.compile(r'(?i)(?:you\s+)?\bignore\b\s+(?:all\s+|any\s+)?(?:prior|previous|above).*\bconstraints?\b'),
    re.compile(r'(?i)let\s+\w+\s+(?:role-?)?play'),
    re.compile(r'(?i)let\'?s\s+(?:role-?)?play'),
]

_SUSPICIOUS_TOKEN_PATTERNS: list[re.Pattern] = [
    re.compile(r'(?i)\bDANGER\b'),
    re.compile(r'(?i)\bINJECTION\b'),
    re.compile(r'(?i)\bOVERFLOW\b'),
    re.compile(r'(?i)PAYLOAD:\s*\{'),
    re.compile(r'(?i)\bSYSTEM\s*(?:MSG|MESSAGE|PROMPT|INSTRUCTION)\s*:'),
    re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]'),
]


@dataclass
class InjectionAnalysis:
    detected: bool
    score: float
    matched_patterns: list[str] = field(default_factory=list)
    confidence: str = "none"

    def should_block(self, threshold: float = 0.3) -> bool:
        return self.score >= threshold


_INJECTION_RESPONSE_BLOCK = (
    "Response blocked — your message could be interpreted as attempting to override "
    "the AI's instructions. Please ask your development question directly."
)


def analyze_prompt_injection(text: str) -> InjectionAnalysis:
    """Analyze user input for prompt injection attempts.

    Returns an InjectionAnalysis with detection score and matched patterns.
    Score is 0.0 (safe) to 1.0 (definitely injection).
    """
    if not text or not isinstance(text, str):
        return InjectionAnalysis(detected=False, score=0.0)

    matched: list[str] = []
    score = 0.0

    for pattern in _KNOWN_INJECTION_PATTERNS:
        if pattern.search(text):
            matched.append(f"injection:{pattern.pattern[:40]}")
            score += 0.25

    for pattern in _SUSPICIOUS_TOKEN_PATTERNS:
        if pattern.search(text):
            matched.append(f"suspicious:{pattern.pattern[:30]}")
            score += 0.35

    if len(text) > 5000:
        score += 0.05

    if "\n" in text:
        line_count = text.count("\n") + 1
        if line_count > 50:
            score += 0.05

    uppper_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if uppper_ratio > 0.7 and len(text) > 100:
        score += 0.1

    score = min(1.0, score)

    confidence = "none"
    if score >= 0.7:
        confidence = "high"
    elif score >= 0.4:
        confidence = "medium"
    elif score >= 0.2:
        confidence = "low"

    return InjectionAnalysis(
        detected=score >= 0.2,
        score=score,
        matched_patterns=matched,
        confidence=confidence,
    )


def get_safe_block_response() -> str:
    return _INJECTION_RESPONSE_BLOCK
