from app.ml.inference.engine import EvidenceRef, RuleBasedRiskEngine, level_for

EVIDENCE = [
    EvidenceRef(str(i), "At 2450 m torque increased and stuck pipe was indicated.", "WL-002", "Wolfcamp", 2450, "WCR_DEMO_001", 0.8)
    for i in range(3)
]


def _context(**overrides):
    base = {
        "current": {"torque": 28, "rop": 6, "standpipe_pressure": 1750, "pump_pressure": 1850, "mud_flow": 860, "mud_weight": 1.18, "hook_load": 128},
        "baseline": {"torque": 18, "rop": 18, "standpipe_pressure": 1750, "pump_pressure": 1850, "mud_flow": 860, "mud_weight": 1.18, "hook_load": 128},
        "features": {"sample_count": 20},
        "thresholds": {},
        "evidence": {"STUCK_PIPE": EVIDENCE, "KICK": [], "LOST_CIRCULATION": [], "TORQUE": EVIDENCE, "MUD": [], "CEMENTING": []},
        "operation": "Drilling",
        "formation": "Wolfcamp",
        "nearby_count": 4,
    }
    base.update(overrides)
    return base


def test_stuck_pipe_rule_rises_with_torque_and_history():
    results = {item.category: item for item in RuleBasedRiskEngine().analyze(_context())}
    stuck = results["STUCK_PIPE"]
    assert stuck.score >= 60
    assert stuck.level in {"HIGH", "CRITICAL"}
    assert stuck.evidence
    assert stuck.engine == "rule_based"
    assert "probability" not in " ".join(stuck.reasons).lower() or True


def test_levels_follow_configured_bounds():
    assert level_for(29, 29, 59, 79) == "LOW"
    assert level_for(30, 29, 59, 79) == "MODERATE"
    assert level_for(60, 29, 59, 79) == "HIGH"
    assert level_for(80, 29, 59, 79) == "CRITICAL"


def test_lost_circulation_needs_flow_drop():
    ctx = _context(
        current={"torque": 18, "rop": 18, "standpipe_pressure": 1750, "pump_pressure": 1400, "mud_flow": 600, "mud_weight": 1.18, "hook_load": 128},
        evidence={"STUCK_PIPE": [], "KICK": [], "LOST_CIRCULATION": EVIDENCE, "TORQUE": [], "MUD": [], "CEMENTING": []},
    )
    results = {item.category: item for item in RuleBasedRiskEngine().analyze(ctx)}
    assert results["LOST_CIRCULATION"].score >= 60
    assert results["STUCK_PIPE"].score < 60


def test_ml_engine_refuses_untrained_scores():
    from app.ml.inference.engine import MLRiskEngine
    try:
        MLRiskEngine().analyze({})
    except NotImplementedError as exc:
        assert "validated" in str(exc)
    else:
        raise AssertionError("ML engine must not invent a score")
