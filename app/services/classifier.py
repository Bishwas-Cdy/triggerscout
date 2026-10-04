import logging
import re
from dataclasses import dataclass

from app.enums import RecommendedAction, Significance, TriggerType
from app.schemas import ChangeResult
from app.services.actions import recommended_action
from app.services.diff import ChangeCandidate
from app.services.llm import LLMClient, LLMError
from app.services.significance import score_significance

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rule:
    trigger: TriggerType
    pattern: re.Pattern[str]
    confidence: float
    rationale: str


_RULES = (
    Rule(
        TriggerType.SALES_TEAM_EXPANSION,
        re.compile(
            r"\b(?:hiring|hire|adding|seeking|openings? for).{0,60}"
            r"(?:account executives?|sales(?:people| reps?| team)?|business development|"
            r"SDRs?|BDRs?)\b",
            re.I,
        ),
        0.94,
        "Sales hiring indicates investment in revenue capacity and go-to-market growth.",
    ),
    Rule(
        TriggerType.FUNDING,
        re.compile(
            r"\b(?:raised|raises|secured|announc(?:e|es|ed|ing)).{0,50}"
            r"(?:(?:\$|€|£)\s?\d[\d,.]*\s?[mkb]?|series\s+[a-f]|funding)\b",
            re.I,
        ),
        0.96,
        "New funding can create budget and urgency for growth initiatives.",
    ),
    Rule(
        TriggerType.ENTERPRISE_EXPANSION,
        re.compile(
            r"\b(?:introducing|launch(?:ing|ed)?|new|now offers?).{0,50}"
            r"enterprise (?:plan|tier|offering|edition)\b",
            re.I,
        ),
        0.92,
        "An enterprise offering signals a move upmarket and changing GTM needs.",
    ),
    Rule(
        TriggerType.MARKET_EXPANSION,
        re.compile(
            r"\b(?:now available|expanding|expanded|launch(?:ing|ed)?|entered|entering)"
            r".{0,80}(?:in|into|across|to)\s+(?:[A-Z][a-z]+|Europe|Asia|APAC|EMEA)",
        ),
        0.91,
        "Geographic expansion suggests new pipeline, localization, and market-entry needs.",
    ),
    Rule(
        TriggerType.NEW_OFFICE,
        re.compile(
            r"\b(?:opened|opening|new) (?:our )?(?:new )?"
            r"(?:office|headquarters|location)\b",
            re.I,
        ),
        0.90,
        "A new office is evidence of operational and geographic growth.",
    ),
    Rule(
        TriggerType.PRICING_CHANGE,
        re.compile(
            r"\b(?:pricing|price|plan).{0,60}(?:changed|updated|increase[ds]?|"
            r"decrease[ds]?|now|per (?:user|month|year))\b|"
            r"\b(?:starting at|now only)\s*(?:\$|€|£)\s?\d",
            re.I,
        ),
        0.90,
        "A pricing change may alter qualification, positioning, and competitive conversations.",
    ),
    Rule(
        TriggerType.NEW_INTEGRATION,
        re.compile(
            r"\b(?:new|launch(?:ed|ing)?|now) (?:native )?integration with\b|"
            r"\bintegrates? with\b",
            re.I,
        ),
        0.90,
        "A new integration creates ecosystem and co-selling opportunities.",
    ),
    Rule(
        TriggerType.PARTNERSHIP,
        re.compile(r"\b(?:partner(?:ed|ship)?|strategic alliance|teams? up) with\b", re.I),
        0.89,
        "A partnership can change distribution, positioning, or account priorities.",
    ),
    Rule(
        TriggerType.LEADERSHIP_CHANGE,
        re.compile(
            r"\b(?:appointed|named|welcomes?|joins? as).{0,60}"
            r"(?:CEO|CRO|CMO|CTO|VP|chief|vice president)\b",
            re.I,
        ),
        0.92,
        "New leadership often prompts strategy, tooling, and vendor reassessment.",
    ),
    Rule(
        TriggerType.SALES_MOTION_CHANGE,
        re.compile(
            r"\b(?:book|request|schedule) (?:a )?(?:demo|consultation)|\btalk to sales\b",
            re.I,
        ),
        0.86,
        "A new sales CTA suggests a shift toward a sales-assisted buying motion.",
    ),
    Rule(
        TriggerType.PRODUCT_LAUNCH,
        re.compile(
            r"\b(?:introducing|announc(?:ing|e|ed)|launch(?:ing|ed)?|"
            r"unveil(?:ing|ed)?)\s+(?:our )?(?:new )?",
            re.I,
        ),
        0.88,
        "A product launch can create new use cases, segments, and outreach timing.",
    ),
    Rule(
        TriggerType.HIRING_GROWTH,
        re.compile(
            r"\b(?:we(?:'re| are) hiring|join our (?:growing )?team|"
            r"\d+ open (?:roles|positions)|hiring \d+)\b",
            re.I,
        ),
        0.88,
        "Broader hiring activity is a practical indicator of company growth.",
    ),
)


def no_change_result(before_excerpt: str = "", after_excerpt: str = "") -> ChangeResult:
    return ChangeResult(
        trigger=TriggerType.NO_MEANINGFUL_CHANGE,
        confidence=1.0,
        significance=Significance.LOW,
        before_excerpt=before_excerpt,
        after_excerpt=after_excerpt,
        why_it_matters="No material GTM signal was found after normalization and noise filtering.",
        recommended_action=RecommendedAction.NO_ACTION,
    )


class TriggerClassifier:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def classify(self, company_name: str, candidate: ChangeCandidate) -> ChangeResult:
        evidence = candidate.after_excerpt
        for rule in _RULES:
            if rule.pattern.search(evidence):
                return ChangeResult(
                    trigger=rule.trigger,
                    confidence=rule.confidence,
                    significance=score_significance(rule.trigger, evidence),
                    before_excerpt=candidate.before_excerpt,
                    after_excerpt=candidate.after_excerpt,
                    why_it_matters=rule.rationale,
                    recommended_action=recommended_action(rule.trigger),
                )
        try:
            llm_result = await self._llm_client.classify(company_name, candidate)
        except LLMError:
            logger.warning("LLM classification failed; using deterministic fallback")
            llm_result = None
        if llm_result is not None:
            return ChangeResult(
                trigger=llm_result.trigger,
                confidence=llm_result.confidence,
                significance=llm_result.significance,
                before_excerpt=candidate.before_excerpt,
                after_excerpt=candidate.after_excerpt,
                why_it_matters=llm_result.why_it_matters,
                recommended_action=llm_result.recommended_action,
            )
        return ChangeResult(
            trigger=TriggerType.GENERAL_CHANGE,
            confidence=0.55,
            significance=Significance.LOW,
            before_excerpt=candidate.before_excerpt,
            after_excerpt=candidate.after_excerpt,
            why_it_matters=(
                "The page changed, but no specific GTM trigger is supported by the evidence."
            ),
            recommended_action=RecommendedAction.RESEARCH_ACCOUNT,
        )
