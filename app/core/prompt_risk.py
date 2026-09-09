import re
from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RiskAssessment:
    level: RiskLevel
    reason: str | None = None


# each pattern is (regex, risk level, human-readable reason)
# case insensitive since nobody's typing jailbreaks in properly capitalized english
_PATTERNS: list[tuple[re.Pattern, RiskLevel, str]] = [
    (re.compile(r"ignore\s+(all\s+|any\s+|previous\s+|prior\s+|the above\s+)*instructions", re.I), RiskLevel.HIGH, "instruction override attempt"),
    (re.compile(r"disregard (your|all|any)\s+(previous|prior)\s+(instructions|rules)", re.I), RiskLevel.HIGH, "instruction override attempt"),
    (re.compile(r"you are now|you're now|act as if you", re.I), RiskLevel.MEDIUM, "role reassignment attempt"),
    (re.compile(r"reveal your (system prompt|instructions|rules)", re.I), RiskLevel.HIGH, "system prompt extraction attempt"),
    (re.compile(r"what (are|is) your (system prompt|instructions)", re.I), RiskLevel.MEDIUM, "system prompt extraction attempt"),
    (re.compile(r"\bDAN\b|\bjailbreak\b|\bunfiltered mode\b", re.I), RiskLevel.HIGH, "known jailbreak terminology"),
    (re.compile(r"pretend (you have no|there are no)\s+(restrictions|rules|guidelines)", re.I), RiskLevel.HIGH, "restriction bypass attempt"),
]

# a wall of base64 in a chat message is a little suspicious on its own,
# people don't usually type "aGVsbG8gd29ybGQ=" 
_SUSPICIOUS_ENCODING = re.compile(r"[A-Za-z0-9+/]{80,}={0,2}")


def assess_risk(text: str) -> RiskAssessment:
    for pattern, level, reason in _PATTERNS:
        if pattern.search(text):
            return RiskAssessment(level=level, reason=reason)

    if _SUSPICIOUS_ENCODING.search(text):
        return RiskAssessment(level=RiskLevel.MEDIUM, reason="long encoded blob in message")

    return RiskAssessment(level=RiskLevel.LOW)


def assess_payload(payload: dict) -> RiskAssessment:
    """
    Runs risk assessment across every message in the request, not just the
    last one, since someone could plant something suspicious a few turns back.
    Returns the highest risk level found across the whole conversation.
    """
    messages = payload.get("messages", [])
    worst = RiskAssessment(level=RiskLevel.LOW)

    severity_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}

    for message in messages:
        content = message.get("content", "")
        if not isinstance(content, str):
            continue
        result = assess_risk(content)
        if severity_order[result.level] > severity_order[worst.level]:
            worst = result

    return worst