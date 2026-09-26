"""Risk engine boundary.

RuleBasedRiskEngine is the active engine.
MLRiskEngine is an interface only. It refuses to return a score because no
model has been trained or validated in this deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.ml.features.feature_builder import percent_change

ENGINE_VERSION = "1.0.0"

CATEGORIES = [
    ("MUD", "Mud Problems"),
    ("STUCK_PIPE", "Stuck Pipe"),
    ("KICK", "Kick / Overpressure"),
    ("TORQUE", "Torque Anomalies"),
    ("CEMENTING", "Cementing Problems"),
    ("LOST_CIRCULATION", "Lost Circulation"),
]


@dataclass
class EvidenceRef:
    id: str
    text_excerpt: str
    well_code: str | None
    formation: str | None
    depth_start: float | None
    report_title: str | None
    confidence: float


@dataclass
class RiskResult:
    category: str
    label: str
    score: float
    level: str
    confidence: float
    reasons: list[str]
    evidence: list[EvidenceRef] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)
    engine: str = "rule_based"
    engine_version: str = ENGINE_VERSION


class RiskEngine(Protocol):
    def analyze(self, context: dict) -> list[RiskResult]: ...


def level_for(score: float, low_max: float, moderate_max: float, high_max: float) -> str:
    if score <= low_max:
        return "LOW"
    if score <= moderate_max:
        return "MODERATE"
    if score <= high_max:
        return "HIGH"
    return "CRITICAL"


def _clamp(score: float) -> float:
    return round(max(0.0, min(100.0, score)), 1)


class RuleBasedRiskEngine:
    """Transparent rules. See docs/RISK_RULES.md."""

    def analyze(self, context: dict) -> list[RiskResult]:
        current = context.get("current") or {}
        baseline = context.get("baseline") or {}
        features = context.get("features") or {}
        thresholds = context.get("thresholds") or {}
        evidence_by_cat: dict[str, list[EvidenceRef]] = context.get("evidence") or {}
        operation = (context.get("operation") or "").lower()
        formation = context.get("formation")
        sample_count = int(features.get("sample_count") or 0)
        nearby_count = int(context.get("nearby_count") or 0)

        def confidence_for(evidence: list[EvidenceRef]) -> float:
            value = 0.35
            if sample_count >= 10:
                value += 0.15
            elif sample_count >= 3:
                value += 0.08
            if evidence:
                value += 0.2
            if nearby_count >= 2:
                value += 0.15
            if formation:
                value += 0.1
            if sample_count == 0:
                value = 0.2
            return round(min(value, 0.95), 2)

        def threshold(category: str) -> dict:
            return thresholds.get(category) or {
                "low_max": 29,
                "moderate_max": 59,
                "high_max": 79,
                "torque_rise_pct": 15,
                "pressure_rise_pct": 10,
                "flow_change_pct": 12,
            }

        results: list[RiskResult] = []

        torque_pct = percent_change(current.get("torque"), baseline.get("torque"))
        rop_pct = percent_change(current.get("rop"), baseline.get("rop"))
        spp_pct = percent_change(current.get("standpipe_pressure"), baseline.get("standpipe_pressure"))
        pump_pct = percent_change(current.get("pump_pressure"), baseline.get("pump_pressure"))
        flow_pct = percent_change(current.get("mud_flow"), baseline.get("mud_flow"))
        mw_pct = percent_change(current.get("mud_weight"), baseline.get("mud_weight"))
        hook_pct = percent_change(current.get("hook_load"), baseline.get("hook_load"))

        # Stuck pipe
        th = threshold("STUCK_PIPE")
        reasons = []
        score = 0.0
        if sample_count == 0:
            reasons.append("Insufficient current parameter data for a stuck-pipe indicator.")
        else:
            if torque_pct is not None and torque_pct >= th["torque_rise_pct"] and (rop_pct is None or rop_pct <= -10):
                score += 40
                reasons.append(
                    f"Torque is {torque_pct:.1f}% above the recent baseline while ROP is not increasing. Rule: rapid torque rise with ROP drop raises the stuck-pipe indicator."
                )
            elif torque_pct is not None and torque_pct >= th["torque_rise_pct"] / 2:
                score += 18
                reasons.append(f"Torque is {torque_pct:.1f}% above the recent baseline.")
            ev = evidence_by_cat.get("STUCK_PIPE", [])
            if ev:
                score += min(30, 12 * len(ev))
                reasons.append(
                    f"{len(ev)} historical stuck-pipe evidence record(s) were found in nearby or similar wells."
                )
            if not reasons:
                reasons.append("No stuck-pipe rule fired on the current parameter window.")
        ev = evidence_by_cat.get("STUCK_PIPE", [])
        results.append(
            RiskResult(
                "STUCK_PIPE",
                "Stuck Pipe",
                _clamp(score),
                level_for(score, th["low_max"], th["moderate_max"], th["high_max"]),
                confidence_for(ev),
                reasons,
                ev,
                {"torque_change_pct": torque_pct, "rop_change_pct": rop_pct},
                features,
            )
        )

        # Kick / overpressure
        th = threshold("KICK")
        reasons = []
        score = 0.0
        pressure_hit = False
        if spp_pct is not None and spp_pct >= th["pressure_rise_pct"]:
            score += 28
            pressure_hit = True
            reasons.append(
                f"Standpipe pressure is {spp_pct:.1f}% above baseline. Rule: unusual pressure rise increases the kick/overpressure indicator."
            )
        if pump_pct is not None and pump_pct >= th["pressure_rise_pct"]:
            score += 18
            pressure_hit = True
            reasons.append(f"Pump pressure is {pump_pct:.1f}% above baseline.")
        ev = evidence_by_cat.get("KICK", [])
        if pressure_hit and ev:
            score += min(34, 14 * len(ev))
            reasons.append(
                f"Nearby historical wells contain {len(ev)} kick/overpressure evidence record(s) used for comparison."
            )
        elif ev:
            score += min(15, 5 * len(ev))
            reasons.append(f"{len(ev)} historical kick/overpressure evidence record(s) exist, without a current pressure rise.")
        if not reasons:
            reasons.append("No kick/overpressure rule fired on the current parameter window.")
        results.append(
            RiskResult(
                "KICK",
                "Kick / Overpressure",
                _clamp(score),
                level_for(score, th["low_max"], th["moderate_max"], th["high_max"]),
                confidence_for(ev),
                reasons,
                ev,
                {"standpipe_change_pct": spp_pct, "pump_change_pct": pump_pct},
                features,
            )
        )

        # Lost circulation
        th = threshold("LOST_CIRCULATION")
        reasons = []
        score = 0.0
        flow_hit = False
        if flow_pct is not None and flow_pct <= -th["flow_change_pct"]:
            score += 34
            flow_hit = True
            reasons.append(
                f"Mud flow is {abs(flow_pct):.1f}% below baseline. Rule: a significant mud-flow drop increases the lost-circulation indicator."
            )
        if pump_pct is not None and pump_pct <= -th["flow_change_pct"] and (mw_pct is None or abs(mw_pct) < 5):
            score += 16
            flow_hit = True
            reasons.append("Pump pressure dropped while mud weight stayed near baseline.")
        ev = evidence_by_cat.get("LOST_CIRCULATION", [])
        if flow_hit and ev:
            score += min(30, 12 * len(ev))
            reasons.append(f"{len(ev)} historical lost-circulation evidence record(s) support the comparison.")
        elif ev:
            score += min(12, 4 * len(ev))
            reasons.append(f"{len(ev)} historical lost-circulation evidence record(s) exist without a current flow drop.")
        if not reasons:
            reasons.append("No lost-circulation rule fired on the current parameter window.")
        results.append(
            RiskResult(
                "LOST_CIRCULATION",
                "Lost Circulation",
                _clamp(score),
                level_for(score, th["low_max"], th["moderate_max"], th["high_max"]),
                confidence_for(ev),
                reasons,
                ev,
                {"flow_change_pct": flow_pct, "pump_change_pct": pump_pct},
                features,
            )
        )

        # Torque anomaly (distinct from stuck-pipe combination)
        th = threshold("TORQUE")
        reasons = []
        score = 0.0
        if torque_pct is not None and abs(torque_pct) >= th["torque_rise_pct"]:
            score += 36
            direction = "above" if torque_pct > 0 else "below"
            reasons.append(
                f"Torque is {abs(torque_pct):.1f}% {direction} the recent baseline. This is a torque-anomaly indicator, separate from the stuck-pipe combination rule."
            )
        ev = evidence_by_cat.get("TORQUE", [])
        if ev and score > 0:
            score += min(24, 10 * len(ev))
            reasons.append(f"{len(ev)} historical torque evidence record(s) were found at comparable conditions.")
        elif ev:
            score += min(10, 4 * len(ev))
            reasons.append(f"{len(ev)} historical torque evidence record(s) exist. Current torque is inside the configured band.")
        if not reasons:
            reasons.append("Torque is within the configured band relative to the recent baseline.")
        results.append(
            RiskResult(
                "TORQUE",
                "Torque Anomalies",
                _clamp(score),
                level_for(score, th["low_max"], th["moderate_max"], th["high_max"]),
                confidence_for(ev),
                reasons,
                ev,
                {"torque_change_pct": torque_pct},
                features,
            )
        )

        # Mud
        th = threshold("MUD")
        reasons = []
        score = 0.0
        if mw_pct is not None and abs(mw_pct) >= 4:
            score += 30
            reasons.append(
                f"Mud weight changed {mw_pct:.1f}% versus the recent baseline. Rule: mud-weight deviation raises the mud-problem indicator."
            )
        ev = evidence_by_cat.get("MUD", [])
        if ev:
            score += min(25, 10 * len(ev))
            reasons.append(f"{len(ev)} historical mud-problem evidence record(s) were retrieved.")
        if not reasons:
            reasons.append("No mud-problem rule fired on the current parameter window.")
        results.append(
            RiskResult(
                "MUD",
                "Mud Problems",
                _clamp(score),
                level_for(score, th["low_max"], th["moderate_max"], th["high_max"]),
                confidence_for(ev),
                reasons,
                ev,
                {"mud_weight_change_pct": mw_pct},
                features,
            )
        )

        # Cementing — historical and operation context, not an autonomous instruction
        th = threshold("CEMENTING")
        reasons = []
        score = 0.0
        if "cement" in operation:
            score += 20
            reasons.append("The current operation is recorded as cementing. Historical cementing evidence is included for review.")
        if hook_pct is not None and "cement" in operation and abs(hook_pct) >= 15:
            score += 20
            reasons.append(f"Hook load changed {hook_pct:.1f}% during a cementing operation.")
        ev = evidence_by_cat.get("CEMENTING", [])
        if ev:
            score += min(30, 12 * len(ev))
            reasons.append(f"{len(ev)} historical cementing evidence record(s) match this formation or nearby wells.")
        if not reasons:
            reasons.append("No cementing rule fired. Current operation is not recorded as cementing and no supporting evidence was matched.")
        results.append(
            RiskResult(
                "CEMENTING",
                "Cementing Problems",
                _clamp(score),
                level_for(score, th["low_max"], th["moderate_max"], th["high_max"]),
                confidence_for(ev),
                reasons,
                ev,
                {"operation": operation, "hook_load_change_pct": hook_pct},
                features,
            )
        )
        return results


class MLRiskEngine:
    def analyze(self, context: dict) -> list[RiskResult]:
        raise NotImplementedError(
            "MLRiskEngine has no trained, validated model in this deployment. "
            "Use RuleBasedRiskEngine. Do not display an accuracy figure."
        )


def get_risk_engine() -> RiskEngine:
    from app.core.config import get_settings

    name = get_settings().risk_engine
    if name == "ml":
        return MLRiskEngine()
    return RuleBasedRiskEngine()
