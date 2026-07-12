"""
Agent 1: Triage Agent
Classifies the incident type, severity, affected systems, and blast radius.
Maps to relevant MITRE ATT&CK techniques and identifies immediate actions.

Incident types supported:
  - ransomware
  - phishing / credential_compromise
  - insider_threat
  - data_breach
  - cloud_misconfiguration
  - malware
  - ddos
  - unknown
"""
# Developed with AI assistance (Claude)

import json
import logging
from langchain_core.messages import HumanMessage

from config.settings import get_llm, ORG_NAME
from agents.state import AgentState

logger = logging.getLogger(__name__)

TRIAGE_PROMPT = """You are an expert incident response analyst performing initial triage for {org_name}.

Organization context:
{org_context}

Incident reported by responder:
\"\"\"{incident_description}\"\"\"

Perform a rapid triage of this incident. Classify it and provide actionable immediate guidance.

Return a JSON object with the following fields:
- incident_type: One of "ransomware" | "phishing" | "credential_compromise" | "insider_threat" | "data_breach" | "cloud_misconfiguration" | "malware" | "ddos" | "unknown"
- severity: "Critical" | "High" | "Medium" | "Low"
  - Critical: Active threat spreading, patient safety at risk, mass PHI exposure, or full system compromise
  - High: Confirmed breach, active attacker, significant data at risk
  - Medium: Suspected incident, limited scope, contained risk
  - Low: Anomaly detected, no confirmed impact
- affected_systems: List of specific systems, assets, or user groups impacted based on the description
- blast_radius: 1-2 sentences describing how far this could spread if not contained immediately
- mitre_techniques: List of 3-5 most relevant MITRE ATT&CK techniques. Each as:
  {{
    "id": "T1566.001",
    "name": "Spearphishing Attachment",
    "tactic": "Initial Access",
    "relevance": "Why this technique applies to this incident"
  }}
- immediate_actions: List of 3-5 things the responder should do RIGHT NOW (in the next 15 minutes), before the full playbook
- triage_summary: 2-3 sentence summary of the incident, its severity, and urgency

Be specific to the org context. If the incident involves Epic EHR, Azure, Active Directory, or known gaps (no SIEM, no EDR, 35% MFA), call that out explicitly.

Return only valid JSON:"""


def run_triage_node(state: AgentState) -> AgentState:
    """LangGraph node for the Triage Agent."""
    logger.info("Triage Agent: Starting incident classification")
    state["current_step"] = "triage"
    state["progress_messages"] = state.get("progress_messages", [])
    state["progress_messages"].append("Triage Agent: Classifying incident...")

    try:
        llm = get_llm()
        prompt = TRIAGE_PROMPT.format(
            org_name=state.get("org_name", ORG_NAME),
            org_context=state.get("org_context", ""),
            incident_description=state["incident_description"],
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        triage_data = _parse_triage(response.content)

        state["incident_type"] = triage_data.get("incident_type", "unknown")
        state["severity"] = triage_data.get("severity", "High")
        state["affected_systems"] = triage_data.get("affected_systems", [])
        state["blast_radius"] = triage_data.get("blast_radius", "")
        state["mitre_techniques"] = triage_data.get("mitre_techniques", [])
        state["immediate_actions"] = triage_data.get("immediate_actions", [])
        state["triage_summary"] = triage_data.get("triage_summary", "")

        fallback_flags = state.get("fallback_flags") or {}
        fallback_flags["triage"] = "llm_generated"
        state["fallback_flags"] = fallback_flags

        state["progress_messages"].append(
            f"Triage Agent: {state['incident_type'].replace('_', ' ').title()} — "
            f"Severity {state['severity']} ✓"
        )
        logger.info(f"Triage complete: {state['incident_type']} / {state['severity']}")

    except Exception as e:
        logger.error(f"Triage Agent error: {e}")
        state["errors"] = state.get("errors", []) + [f"Triage Agent: {str(e)}"]
        _apply_fallback(state)

    return state


def _parse_triage(content: str) -> dict:
    """Parse JSON triage result from LLM response."""
    try:
        content = content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except Exception as e:
        logger.warning(f"Triage JSON parse failed: {e}")
    return {}


def _apply_fallback(state: AgentState) -> None:
    """Apply conservative fallback triage when LLM fails."""
    state["incident_type"] = state.get("incident_type") or "unknown"
    state["severity"] = state.get("severity") or "High"
    state["affected_systems"] = state.get("affected_systems") or ["Unknown — manual assessment required"]
    state["blast_radius"] = state.get("blast_radius") or "Scope undetermined. Treat as high-impact until assessed."
    state["mitre_techniques"] = state.get("mitre_techniques") or []
    state["immediate_actions"] = state.get("immediate_actions") or [
        "Isolate the affected system(s) from the network immediately",
        "Preserve logs and system state before making changes",
        "Notify your IT Director and document the time of discovery",
        "Do not power off affected systems — this destroys volatile forensic evidence",
        "Begin incident log — record every action with timestamp",
    ]
    state["triage_summary"] = state.get("triage_summary") or (
        "Incident classification unavailable due to an error. "
        "Proceed with conservative containment measures and manual assessment."
    )
    fallback_flags = state.get("fallback_flags") or {}
    fallback_flags["triage"] = "fallback_static"
    state["fallback_flags"] = fallback_flags
