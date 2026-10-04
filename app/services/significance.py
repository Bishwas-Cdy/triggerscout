import re

from app.enums import Significance, TriggerType

_HIGH_IMPACT = {
    TriggerType.SALES_TEAM_EXPANSION,
    TriggerType.FUNDING,
    TriggerType.ENTERPRISE_EXPANSION,
    TriggerType.MARKET_EXPANSION,
    TriggerType.LEADERSHIP_CHANGE,
}


def score_significance(trigger: TriggerType, evidence: str) -> Significance:
    if trigger is TriggerType.NO_MEANINGFUL_CHANGE:
        return Significance.LOW
    quantified = bool(
        re.search(
            r"(?:\$|€|£)\s?\d|\b\d+\s+(?:roles?|people|hires?|countries|"
            r"account executives?|sales reps?|SDRs?|BDRs?)",
            evidence,
            re.I,
        )
    )
    if trigger in _HIGH_IMPACT and quantified:
        return Significance.HIGH
    if trigger in _HIGH_IMPACT or trigger in {
        TriggerType.PRODUCT_LAUNCH,
        TriggerType.PRICING_CHANGE,
        TriggerType.SALES_MOTION_CHANGE,
    }:
        return Significance.MEDIUM
    return Significance.LOW
