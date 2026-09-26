"""Hybrid extraction for drilling reports.

Order of use:
1. Regular expressions for depth, dates, and parameter values.
2. Rule lexicon for events, actions, outcomes, equipment, and risks.
3. spaCy entity ruler and noun phrases when a model is installed.
4. Transformer models are not loaded unless ENABLE_TRANSFORMERS is set.
   No transformer weights ship with DrillLens, so this path stays inactive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.logging import log

EVENT_RULES: list[tuple[str, str, str]] = [
    (r"stuck[\s-]*pipe|pipe\s+stuck|differentially\s+stuck", "STUCK_PIPE", "STUCK_PIPE"),
    (r"lost\s+circulation|loss\s+of\s+circulation|losses\b|lost\s+returns", "LOST_CIRCULATION", "LOST_CIRCULATION"),
    (r"\bkick\b|influx|well\s+control", "KICK", "KICK"),
    (r"overpressure|over-?pressured|abnormal\s+pressure", "OVERPRESSURE", "KICK"),
    (r"torque\s+(increased|increase|spike|rose|high)|high\s+torque|torque\s+anomal", "TORQUE", "TORQUE"),
    (r"cement(ing)?\s+(problem|failure|channel|job)|poor\s+cement|cement\s+bond", "CEMENTING", "CEMENTING"),
    (r"mud\s+(loss|problem|contamination)|gas-?cut\s+mud|viscosity\s+(increased|rose)|bit\s+balling", "MUD", "MUD"),
]

ACTION_RULES = [
    (r"wob\s+was\s+reduced|reduced\s+wob|lowered\s+wob", "Reduced WOB"),
    (r"rpm\s+was\s+reduced|reduced\s+rpm", "Reduced RPM"),
    (r"lcm\s+was\s+pumped|pumped\s+lcm|spotted\s+lcm", "Pumped LCM"),
    (r"well\s+was\s+shut\s+in|shut\s+in\s+the\s+well", "Shut in the well"),
    (r"circulated|circulation\s+was", "Circulated"),
    (r"weight(?:ed)?\s+up|increased\s+mud\s+weight", "Increased mud weight"),
    (r"reamed|backream", "Reamed"),
    (r"worked\s+(the\s+)?pipe|jarred", "Worked the pipe"),
]

OUTCOME_RULES = [
    (r"torque\s+stabiliz\w+", "Torque stabilized"),
    (r"circulation\s+was\s+partially\s+restored|returns\s+restored|circulation\s+restored", "Circulation restored"),
    (r"pressure\s+stabiliz\w+", "Pressure stabilized"),
    (r"pipe\s+(was\s+)?freed|freed\s+the\s+pipe", "Pipe freed"),
    (r"no\s+further\s+(losses|influx)", "Condition stabilized"),
    (r"cement\s+job\s+completed|squeeze\s+successful", "Cement job completed"),
]

EQUIPMENT_RULES = [
    (r"\bBHA\b", "BHA"),
    (r"\bPDC\b|\bbit\b", "Bit"),
    (r"mud\s+motor|motor", "Mud motor"),
    (r"\bjars?\b", "Jar"),
    (r"stabilizer", "Stabilizer"),
    (r"casing", "Casing"),
]

PARAM_RULES = [
    (r"WOB\s+(?:was\s+)?(\d+(?:\.\d+)?)\s*(klbf|t|tonnes?)?", "DRILLING_PARAMETER", "WOB"),
    (r"RPM\s+(?:was\s+)?(\d+(?:\.\d+)?)", "DRILLING_PARAMETER", "RPM"),
    (r"torque\s+(?:was\s+|of\s+)?(\d+(?:\.\d+)?)\s*(kN\.?m|klbf)", "DRILLING_PARAMETER", "TORQUE"),
    (r"mud\s+weight\s+(?:was\s+|of\s+)?(\d+(?:\.\d+)?)\s*(sg|ppg)?", "DRILLING_PARAMETER", "MUD_WEIGHT"),
    (r"ROP\s+(?:was\s+)?(\d+(?:\.\d+)?)", "DRILLING_PARAMETER", "ROP"),
]

DEPTH_RE = re.compile(r"(\d{3,5}(?:\.\d+)?)\s*(m|ft|meters|feet)\b", re.I)
FORMATION_RE = re.compile(
    r"([A-Z][A-Za-z0-9][A-Za-z0-9\- ]{1,40}?)\s+Formation",
)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Z][a-z]+\s+\d{4})\b")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Entity:
    entity_type: str
    text: str
    normalized_value: str | None
    confidence: float
    extractor: str
    start_char: int | None = None
    end_char: int | None = None


@dataclass
class ExtractedEvent:
    depth_start: float | None
    depth_end: float | None
    formation: str | None
    event_type: str
    description: str
    action_taken: str | None
    outcome: str | None
    risk_category: str
    event_date: str | None
    confidence: float
    entities: list[Entity] = field(default_factory=list)


_nlp = None
_nlp_tried = False


def _load_spacy():
    global _nlp, _nlp_tried
    if _nlp_tried:
        return _nlp
    _nlp_tried = True
    settings = get_settings()
    if not settings.enable_spacy:
        return None
    try:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
        ruler = _nlp.add_pipe("entity_ruler", before="ner")
        patterns = []
        for name in ("Wolfcamp", "Bone Spring", "Spraberry", "Dean", "Strawn"):
            patterns.append({"label": "FORMATION", "pattern": name})
        patterns.extend(
            [
                {"label": "EVENT", "pattern": "stuck pipe"},
                {"label": "EVENT", "pattern": "lost circulation"},
                {"label": "EVENT", "pattern": "kick"},
                {"label": "RISK", "pattern": "overpressure"},
            ]
        )
        ruler.add_patterns(patterns)
        log.info("spaCy model en_core_web_sm loaded for NLP extraction")
    except Exception as exc:  # pragma: no cover - optional model
        log.info("spaCy model unavailable; using regex and rules only (%s)", exc)
        _nlp = None
    return _nlp


def _spacy_entities(text: str) -> list[Entity]:
    nlp = _load_spacy()
    if nlp is None:
        return []
    doc = nlp(text[:100000])
    found: list[Entity] = []
    for ent in doc.ents:
        if ent.label_ in {"DATE", "FORMATION", "EVENT", "RISK", "ORG", "GPE"}:
            etype = ent.label_
            if etype == "DATE":
                etype = "DATE"
            elif etype in {"ORG", "GPE"}:
                etype = "EQUIPMENT" if etype == "ORG" else "FORMATION"
            found.append(
                Entity(
                    entity_type=etype if etype in {"DATE", "FORMATION", "EVENT", "RISK", "EQUIPMENT"} else "FORMATION",
                    text=ent.text,
                    normalized_value=ent.text,
                    confidence=0.62,
                    extractor="SPACY",
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                )
            )
    return found


def extract_entities(text: str) -> list[Entity]:
    entities: list[Entity] = []
    for match in DEPTH_RE.finditer(text):
        unit = match.group(2).lower()
        value = float(match.group(1))
        if unit in {"ft", "feet"}:
            value = round(value * 0.3048, 2)
            shown = f"{value} m"
        else:
            shown = match.group(0)
        entities.append(
            Entity("DEPTH", shown, str(value), 0.9, "REGEX", match.start(), match.end())
        )
    for match in FORMATION_RE.finditer(text):
        name = match.group(1).strip()
        entities.append(
            Entity("FORMATION", f"{name} Formation", name, 0.86, "REGEX", match.start(), match.end())
        )
    for match in DATE_RE.finditer(text):
        entities.append(Entity("DATE", match.group(1), match.group(1), 0.8, "REGEX", match.start(), match.end()))
    for pattern, etype, label in PARAM_RULES:
        for match in re.finditer(pattern, text, re.I):
            entities.append(
                Entity(etype, match.group(0), f"{label}={match.group(1)}", 0.78, "RULE", match.start(), match.end())
            )
    for pattern, label in EQUIPMENT_RULES:
        for match in re.finditer(pattern, text, re.I):
            entities.append(Entity("EQUIPMENT", match.group(0), label, 0.7, "RULE", match.start(), match.end()))
    entities.extend(_spacy_entities(text))
    # Deduplicate overlapping identical spans.
    unique: list[Entity] = []
    seen = set()
    for ent in entities:
        key = (ent.entity_type, ent.text.lower(), ent.start_char)
        if key in seen:
            continue
        seen.add(key)
        unique.append(ent)
    return unique


def _first(rules: list[tuple[str, str]], sentence: str) -> str | None:
    for pattern, label in rules:
        if re.search(pattern, sentence, re.I):
            return label
    return None


def extract_events(text: str, report_date: str | None = None) -> list[ExtractedEvent]:
    """Split a report into sentences and build structured drilling events."""
    entities = extract_entities(text)
    sentences = [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]
    events: list[ExtractedEvent] = []
    header_date = report_date
    for ent in entities:
        if ent.entity_type == "DATE" and header_date is None:
            header_date = ent.normalized_value

    for sentence in sentences:
        matched = None
        for pattern, event_type, risk in EVENT_RULES:
            if re.search(pattern, sentence, re.I):
                matched = (event_type, risk)
                break
        if not matched:
            continue
        event_type, risk = matched
        depths = [float(m.group(1)) if m.group(2).lower() in {"m", "meters"} else round(float(m.group(1)) * 0.3048, 2)
                  for m in DEPTH_RE.finditer(sentence)]
        # recompute with unit conversion already in list above — fix feet
        depths = []
        for m in DEPTH_RE.finditer(sentence):
            value = float(m.group(1))
            if m.group(2).lower() in {"ft", "feet"}:
                value = round(value * 0.3048, 2)
            depths.append(value)
        formation = None
        fm = FORMATION_RE.search(sentence)
        if fm:
            formation = fm.group(1).strip()
        action = _first(ACTION_RULES, sentence)
        outcome = _first(OUTCOME_RULES, sentence)
        confidence = 0.72
        if depths:
            confidence += 0.1
        if formation:
            confidence += 0.08
        if action:
            confidence += 0.04
        sent_entities = [e for e in entities if e.text and e.text.lower() in sentence.lower()]
        events.append(
            ExtractedEvent(
                depth_start=depths[0] if depths else None,
                depth_end=depths[-1] if len(depths) > 1 else (depths[0] if depths else None),
                formation=formation,
                event_type=event_type,
                description=sentence,
                action_taken=action,
                outcome=outcome,
                risk_category=risk,
                event_date=header_date,
                confidence=min(confidence, 0.95),
                entities=sent_entities,
            )
        )
    return events


def transformer_status() -> dict:
    settings = get_settings()
    return {
        "enabled": settings.enable_transformers,
        "loaded": False,
        "reason": (
            "No transformer weights are bundled. Risk and extraction use documented rules. "
            "Set ENABLE_TRANSFORMERS only after a validated model is registered."
        ),
    }
