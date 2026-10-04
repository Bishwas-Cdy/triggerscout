from app.enums import RecommendedAction, TriggerType

_ACTION_MAP: dict[TriggerType, RecommendedAction] = {
    TriggerType.HIRING_GROWTH: RecommendedAction.REQUALIFY_ACCOUNT,
    TriggerType.SALES_TEAM_EXPANSION: RecommendedAction.RESEARCH_ACCOUNT,
    TriggerType.FUNDING: RecommendedAction.CREATE_FOLLOW_UP,
    TriggerType.PRODUCT_LAUNCH: RecommendedAction.RESEARCH_ACCOUNT,
    TriggerType.ENTERPRISE_EXPANSION: RecommendedAction.NOTIFY_SALES,
    TriggerType.MARKET_EXPANSION: RecommendedAction.REQUALIFY_ACCOUNT,
    TriggerType.NEW_OFFICE: RecommendedAction.RESEARCH_ACCOUNT,
    TriggerType.PRICING_CHANGE: RecommendedAction.REVIEW_PRICING_CHANGE,
    TriggerType.NEW_INTEGRATION: RecommendedAction.RESEARCH_ACCOUNT,
    TriggerType.PARTNERSHIP: RecommendedAction.RESEARCH_ACCOUNT,
    TriggerType.LEADERSHIP_CHANGE: RecommendedAction.CREATE_FOLLOW_UP,
    TriggerType.SALES_MOTION_CHANGE: RecommendedAction.NOTIFY_SALES,
    TriggerType.GENERAL_CHANGE: RecommendedAction.RESEARCH_ACCOUNT,
    TriggerType.NO_MEANINGFUL_CHANGE: RecommendedAction.NO_ACTION,
}


def recommended_action(trigger: TriggerType) -> RecommendedAction:
    return _ACTION_MAP[trigger]
