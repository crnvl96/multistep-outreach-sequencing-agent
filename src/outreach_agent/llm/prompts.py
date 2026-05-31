import json

from outreach_agent.models import (
    GeneratedEmail,
    IcpScore,
    LeadProfile,
    Route,
    SequencePlan,
)

ICP_DEFINITION = (
    "B2B SaaS or AI/software companies with 50–500 employees, selling to "
    "mid-market or enterprise customers, operating in North America or Europe, "
    "and actively scaling outbound sales or go-to-market operations. Strong "
    "positive signals include SDR/AE/RevOps hiring, recent funding or launch "
    "activity, CRM/sales engagement tooling, manual lead qualification pain, "
    "personalization bottlenecks, or fragmented enrichment workflows. Strong "
    "negative signals include local/B2C businesses, very small companies without "
    "a sales motion, non-software businesses, unclear company identity, or no "
    "credible outbound/GTM need."
)


def build_scoring_messages(profile: LeadProfile) -> list[dict[str, str]]:
    profile_json = json_for_prompt(profile.model_dump(mode="json"))
    score_schema_json = json_for_prompt(IcpScore.model_json_schema())
    return [
        {
            "role": "system",
            "content": (
                "You are an ICP scoring analyst for a GTM automation product. "
                "Return only valid JSON. Do not include markdown fences, prose, "
                "or commentary outside the JSON object."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Documented ICP:\n{ICP_DEFINITION}\n\n"
                "Score the enriched lead profile against the ICP. The application "
                "will choose the final route deterministically, so do not choose "
                "a route.\n\n"
                f"Enriched lead profile:\n{profile_json}\n\n"
                "Return strict structured JSON matching this schema:\n"
                f"{score_schema_json}"
            ),
        },
    ]


def json_for_prompt(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def build_email_messages(
    profile: LeadProfile,
    scoring_result: IcpScore,
    final_route: Route,
    sequence: SequencePlan,
) -> list[dict[str, str]]:
    sequence_json = json_for_prompt(sequence.model_dump(mode="json"))
    profile_json = json_for_prompt(profile.model_dump(mode="json"))
    score_json = json_for_prompt(scoring_result.model_dump(mode="json"))
    email_schema_json = json_for_prompt(GeneratedEmail.model_json_schema())
    return [
        {
            "role": "system",
            "content": (
                "You write first-touch outbound emails for a GTM automation "
                "product. Return only valid JSON. Do not include markdown fences, "
                "prose, or commentary outside the JSON object. Do not invent facts "
                "beyond the lead profile and scoring context."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Final deterministic route: {final_route}\n"
                "Do not change, relabel, or second-guess the route.\n\n"
                f"Selected route instructions:\n{sequence.style}\n\n"
                f"Selected sequence plan:\n{sequence_json}\n\n"
                f"Lead profile:\n{profile_json}\n\n"
                f"Scoring context:\n{score_json}\n\n"
                "Generate only the first email. Return strict structured JSON "
                "matching this schema:\n"
                f"{email_schema_json}"
            ),
        },
    ]


def build_repair_messages(
    original_messages: list[dict[str, str]],
    invalid_output: object,
    repair_prompt: str,
) -> list[dict[str, str]]:
    return [
        *original_messages,
        {
            "role": "assistant",
            "content": stringify_llm_output(invalid_output),
        },
        {
            "role": "user",
            "content": repair_prompt,
        },
    ]


def stringify_llm_output(output: object) -> str:
    if isinstance(output, str):
        return output
    return json_for_prompt(output)


__all__ = [
    "ICP_DEFINITION",
    "build_scoring_messages",
    "build_email_messages",
    "build_repair_messages",
    "json_for_prompt",
    "stringify_llm_output",
]
