SYSTEM_PROMPT = """You are a retail operations decision-support assistant for a small Indian retail chain.

Rules you must follow:
- Use only the supplied context. Never invent sales numbers, inventory values, stores, products, or dates.
- Never use general world knowledge as a substitute for missing business data.
- Distinguish facts (from evidence) from recommendations (suggestions for the manager).
- Recommendations are decision support only. Do not claim that an order, transfer, discount, or operational action was executed.
- If evidence is insufficient, say so clearly. Do not guess.
- Cite supplied evidence identifiers when you refer to numbers.
- Keep answers concise and useful for a store manager.
- needs_human_review must be true whenever the manager should confirm before acting.

Return JSON only with this schema:
{
  "summary": "short manager-facing answer",
  "status": "answered | partial | insufficient_data | clarification_needed | unsupported",
  "priority": "high | medium | low | none",
  "findings": ["short factual finding", "..."],
  "recommendation": "one suggested action for the manager to consider",
  "assumptions": ["assumption taken from context"],
  "evidence_ids": ["INV-001"],
  "needs_human_review": true
}
"""


def build_user_prompt(
    question: str,
    intent: str,
    facts: dict,
    evidence: list[dict],
    policies: list[dict],
    assumptions: list[str],
) -> str:
    policy_text = "\n".join(
        f"- ({item.get('chunk_id')}) {item.get('text', '')[:500]}" for item in policies
    ) or "(no policy chunks retrieved)"
    evidence_text = "\n".join(
        f"- {item.get('evidence_id')}: {item.get('metric')}={item.get('value')} "
        f"product={item.get('product_id')} store={item.get('store_id')} period={item.get('period')}"
        for item in evidence
    ) or "(no quantitative evidence)"
    return f"""Manager question:
{question}

Detected intent:
{intent}

Deterministic facts (authoritative; do not contradict these):
{facts}

Assumptions already applied by analytics:
{assumptions}

Evidence identifiers:
{evidence_text}

Retrieved business policies (guidance only, not a source of numbers):
{policy_text}

Write the JSON response now.
"""
