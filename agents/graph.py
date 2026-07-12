"""
LangGraph Pipeline — IRPlaybookAgent State Machine
Orchestrates the triage → playbook → critic → human review pipeline.

Flow:
  triage → playbook_generation → critic → human_review → [documentation] → END

The advisor loop is handled separately by the Streamlit app calling run_advisor_turn()
for each conversational turn. The documentation agent is called when the user ends the session.
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.triage_agent import run_triage_node
from agents.playbook_agent import run_playbook_node
from agents.critic_agent import run_critic_node
from config.settings import ORG_NAME, ORG_PROFILE

logger = logging.getLogger(__name__)


def run_documentation_node(state: AgentState) -> AgentState:
    """Lazy import to keep documentation agent isolated."""
    from agents.documentation_agent import run_documentation_node as _run
    return _run(state)


def human_review_node(state: AgentState) -> AgentState:
    """
    Human-in-the-loop node: pauses pipeline for responder review.
    In CLI mode: auto-approves.
    In Streamlit mode: Streamlit handles the review UI.
    """
    state["current_step"] = "human_review"
    if state.get("approved") is None:
        state["approved"] = True  # CLI mode: auto-approve
    state["progress_messages"] = state.get("progress_messages", [])
    state["progress_messages"].append("Playbook ready for review")
    return state


def should_generate_report(state: AgentState) -> Literal["documentation", "human_review"]:
    """Conditional edge: only generate report if session is complete and approved."""
    if state.get("approved") and state.get("session_complete"):
        return "documentation"
    return "human_review"


def build_graph(include_documentation: bool = True) -> StateGraph:
    """Build and compile the IRPlaybookAgent LangGraph."""
    graph = StateGraph(AgentState)

    graph.add_node("triage", run_triage_node)
    graph.add_node("playbook_generation", run_playbook_node)
    graph.add_node("critic", run_critic_node)
    graph.add_node("human_review", human_review_node)

    if include_documentation:
        graph.add_node("documentation", run_documentation_node)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "playbook_generation")
    graph.add_edge("playbook_generation", "critic")
    graph.add_edge("critic", "human_review")

    if include_documentation:
        graph.add_conditional_edges(
            "human_review",
            should_generate_report,
            {
                "documentation": "documentation",
                "human_review": "human_review",
            }
        )
        graph.add_edge("documentation", END)
    else:
        graph.add_edge("human_review", END)

    return graph.compile()


def _build_org_context() -> str:
    """Build the org context string from org_profile.json for agent prompts."""
    profile = ORG_PROFILE
    gaps = "\n".join(f"  - {g}" for g in profile.get("security_gaps", []))
    systems = ", ".join(profile.get("key_systems", []))
    incidents = "; ".join(
        f"{i['id']} ({i['type']})" for i in profile.get("known_incidents", [])
    )
    return (
        f"Organization: {profile.get('org_name')} | Industry: {profile.get('industry')}\n"
        f"Size: {profile.get('size', {}).get('employees', 'Unknown')} employees | "
        f"Regulatory: {', '.join(profile.get('regulatory_frameworks', []))}\n"
        f"Environment: {profile.get('environment', {}).get('type', 'Unknown')}\n"
        f"Key Systems: {systems}\n"
        f"Known Security Gaps:\n{gaps}\n"
        f"Prior Incidents: {incidents}"
    )


def run_initial_pipeline(
    incident_description: str,
    approved: bool = True,
) -> AgentState:
    """
    Run the initial triage → playbook → critic pipeline.

    Args:
        incident_description: Natural language description of the incident
        approved: Whether to auto-approve for CLI runs

    Returns:
        AgentState with triage, playbook, and critic results populated
    """
    initial_state: AgentState = {
        "incident_description": incident_description,
        "org_name": ORG_NAME,
        "org_context": _build_org_context(),
        "incident_type": None,
        "severity": None,
        "affected_systems": None,
        "blast_radius": None,
        "mitre_techniques": None,
        "immediate_actions": None,
        "triage_summary": None,
        "playbook_phases": None,
        "playbook_summary": None,
        "critic_issues": None,
        "critic_approved": None,
        "revised_playbook_phases": None,
        "conversation_history": [],
        "constraints": [],
        "advisor_response": None,
        "session_complete": False,
        "incident_timeline": None,
        "lessons_learned": None,
        "hipaa_assessment": None,
        "report_path": None,
        "current_step": "starting",
        "approved": approved,
        "errors": [],
        "progress_messages": [],
        "fallback_flags": {},
    }

    app = build_graph(include_documentation=False)
    logger.info(f"Starting IRPlaybookAgent pipeline | incident={incident_description[:80]}...")
    final_state = app.invoke(initial_state)
    logger.info(f"Initial pipeline complete | type={final_state.get('incident_type')} | "
                f"severity={final_state.get('severity')} | errors={len(final_state.get('errors', []))}")
    return final_state


# ── CLI Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

    print("\n" + "="*60)
    print("  IRPlaybookAgent — Incident Response Pipeline")
    print("="*60)
    incident = input("\nDescribe the incident: ").strip()
    if not incident:
        incident = ("Ransomware detected on 3 clinical workstations in the cardiology unit. "
                    "Files are actively encrypting. We're on a hybrid Azure + on-premises network "
                    "with Epic EHR running.")
        print(f"\nUsing demo incident: {incident}")

    result = run_initial_pipeline(incident_description=incident)

    print(f"\n{'='*60}")
    print(f"  Triage Complete")
    print(f"{'='*60}")
    print(f"  Incident Type: {result.get('incident_type')}")
    print(f"  Severity:      {result.get('severity')}")
    print(f"  Affected:      {', '.join(result.get('affected_systems', []))}")
    print(f"\n  Immediate Actions:")
    for action in result.get("immediate_actions", []):
        print(f"    → {action}")
    print(f"\n  Playbook Phases: {len(result.get('revised_playbook_phases', []))}")
    print(f"  Critic Issues:   {len(result.get('critic_issues', []))}")
    print(f"  Errors:          {len(result.get('errors', []))}")
    print(f"{'='*60}\n")
