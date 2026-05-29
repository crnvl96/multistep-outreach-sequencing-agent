import pytest

from outreach_agent.models import Confidence, IcpScore, Route
from outreach_agent.workflow import route_from_score


def make_score(score: int, confidence: Confidence = "high") -> IcpScore:
    return IcpScore(
        score=score,
        confidence=confidence,
        positive_evidence=["positive"],
        negative_evidence=[],
        missing_evidence=[],
        reasoning="reasoning",
    )


@pytest.mark.parametrize(
    ("score", "expected_route"),
    [
        (100, "hot"),
        (80, "hot"),
        (79, "warm"),
        (50, "warm"),
        (49, "cold"),
        (0, "cold"),
    ],
)
def test_route_from_score_uses_documented_score_boundaries(
    score: int,
    expected_route: Route,
) -> None:
    assert route_from_score(make_score(score)) == expected_route


@pytest.mark.parametrize("score", [100, 80])
def test_route_from_score_keeps_high_scores_warm_when_confidence_is_low(
    score: int,
) -> None:
    assert route_from_score(make_score(score, confidence="low")) == "warm"
