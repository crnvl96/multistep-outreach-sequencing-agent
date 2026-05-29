import pytest
from pydantic import ValidationError

from outreach_agent.models import LeadIntake


def test_lead_intake_accepts_domain() -> None:
    lead = LeadIntake(
        lead_name="Ada Lovelace",
        company_name="ThinCo",
        company_domain="thinco.example",
    )

    assert lead.lead_name == "Ada Lovelace"
    assert lead.company_name == "ThinCo"
    assert lead.company_domain == "thinco.example"


def test_lead_intake_accepts_email_without_domain() -> None:
    lead = LeadIntake(
        lead_name="Ada Lovelace",
        company_name="ThinCo",
        lead_email="ada@thinco.example",
    )

    assert lead.lead_email == "ada@thinco.example"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "company_name": "ThinCo",
            "company_domain": "thinco.example",
        },
        {
            "lead_name": "Ada Lovelace",
            "company_domain": "thinco.example",
        },
        {
            "lead_name": "Ada Lovelace",
            "company_name": "ThinCo",
        },
    ],
)
def test_lead_intake_rejects_missing_required_fields(
    payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        LeadIntake(**payload)


def test_lead_intake_rejects_extra_fields() -> None:
    payload = {
        "lead_name": "Ada Lovelace",
        "company_name": "ThinCo",
        "company_domain": "thinco.example",
        "unexpected": "nope",
    }

    with pytest.raises(ValidationError):
        LeadIntake(**payload)
