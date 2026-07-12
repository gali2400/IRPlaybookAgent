"""
Agent 5: Documentation Agent
Generates a formal post-incident report at the end of the response session.
Includes incident timeline, actions taken, lessons learned, and HIPAA breach
notification assessment for healthcare organizations.
"""

import json
import logging
import os
from datetime import datetime
from langchain_core.messages import HumanMessage

from config.settings import get_llm, ORG_NAME, ORG_PROFILE, OUTPUT_PATH
from agents.state import AgentState

logger = logging.getLogger(__name__)

DOCUMENTATION_PROMPT = """You are a senior incident response consultant writing a formal post-incident report
for {org_name}.

Organization context:
{org_context}

Incident details:
- Type: {incident_type}
- Severity: {severity}
- Affected Systems: {affected_systems}
- Blast Radius: {blast_radius}
- MITRE Techniques: {mitre_techniques}
- Triage Summary: {triage_summary}

Conversation history (responder actions and advisor guidance):
{conversation_history}

Constraints reported during response:
{constraints}

Generate a formal incident report. Return JSON:
{{
  "incident_id": "INC-{year}-{num}",
  "title": "Brief incident title",
  "executive_summary": "2-3 sentence executive summary suitable for the COO and legal team",
  "incident_timeline": [
    {{
      "timestamp": "Approximate time or 'T+0'",
      "event": "What happened",
      "actor": "Who performed this action"
    }}
  ],
  "actions_taken": [
    "List of containment, eradication, and recovery actions completed during this session"
  ],
  "incomplete_steps": [
    "Playbook steps that were not completed or were constrained"
  ],
  "lessons_learned": [
    "Specific improvements to prevent recurrence or improve future response"
  ],
  "hipaa_assessment": {{
    "phi_involved": true,
    "breach_determination": "Breach confirmed | Breach not confirmed | Risk assessment required",
    "notification_required": true,
    "notification_deadline": "Date (60 days from discovery for HIPAA)",
    "entities_to_notify": ["HHS Office for Civil Rights", "Affected individuals", "Media (if 500+ in same state)"],
    "notes": "Specific HIPAA breach notification guidance for this incident"
  }},
  "root_cause": "Brief root cause analysis",
  "recommendations": [
    "Top 3-5 security improvements to prevent recurrence"
  ]
}}

For the hipaa_assessment, assess whether Protected Health Information (PHI) was or could have been
accessed based on the incident type and affected systems. For MedBridge, Epic EHR contains 340,000
patient records, and Azure Blob Storage (AZ-005) contains radiology PHI.

Return only valid JSON:"""


def run_documentation_node(state: AgentState) -> AgentState:
    """LangGraph node for the Documentation Agent."""
    logger.info("Documentation Agent: Generating incident report")
    state["current_step"] = "documentation"
    state["progress_messages"] = state.get("progress_messages", [])
    state["progress_messages"].append("Documentation Agent: Generating incident report...")

    try:
        llm = get_llm()

        history = state.get("conversation_history") or []
        history_str = "\n".join(
            f"[{m.get('timestamp', '')}] {m['role'].title()}: {m['content']}"
            for m in history
        ) if history else "No conversation recorded."

        constraints = state.get("constraints") or []
        constraints_str = "\n".join(f"- {c}" for c in constraints) if constraints else "None"

        year = datetime.now().year
        num = f"{datetime.now().month:02d}{datetime.now().day:02d}"

        prompt = DOCUMENTATION_PROMPT.format(
            org_name=state.get("org_name", ORG_NAME),
            org_context=state.get("org_context", ""),
            incident_type=state.get("incident_type", "unknown"),
            severity=state.get("severity", "High"),
            affected_systems=", ".join(state.get("affected_systems", [])),
            blast_radius=state.get("blast_radius", ""),
            mitre_techniques=json.dumps(state.get("mitre_techniques", []), indent=2),
            triage_summary=state.get("triage_summary", ""),
            conversation_history=history_str,
            constraints=constraints_str,
            year=year,
            num=num,
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        report_data = _parse_report(response.content)

        state["incident_timeline"] = report_data.get("incident_timeline", [])
        state["lessons_learned"] = report_data.get("lessons_learned", [])
        state["hipaa_assessment"] = report_data.get("hipaa_assessment", {})

        # Save report to file
        report_path = _save_report(report_data, state)
        state["report_path"] = report_path

        fallback_flags = state.get("fallback_flags") or {}
        fallback_flags["documentation"] = "llm_generated"
        state["fallback_flags"] = fallback_flags

        state["progress_messages"].append("Documentation Agent: Incident report generated ✓")
        logger.info(f"Documentation complete: report saved to {report_path}")

    except Exception as e:
        logger.error(f"Documentation Agent error: {e}")
        state["errors"] = state.get("errors", []) + [f"Documentation Agent: {str(e)}"]
        state["incident_timeline"] = state.get("incident_timeline") or []
        state["lessons_learned"] = state.get("lessons_learned") or []
        state["hipaa_assessment"] = state.get("hipaa_assessment") or {}
        fallback_flags = state.get("fallback_flags") or {}
        fallback_flags["documentation"] = "fallback_static"
        state["fallback_flags"] = fallback_flags

    return state


def _parse_report(content: str) -> dict:
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
        logger.warning(f"Report parse failed: {e}")
    return {}


def _save_report(report_data: dict, state: AgentState) -> str:
    """Save the incident report as a JSON file."""
    try:
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        incident_type = state.get("incident_type", "unknown").replace("_", "-")
        filename = f"incident_report_{incident_type}_{timestamp}.json"
        report_path = os.path.join(OUTPUT_PATH, filename)

        full_report = {
            **report_data,
            "org_name": state.get("org_name", ORG_NAME),
            "incident_type": state.get("incident_type"),
            "severity": state.get("severity"),
            "affected_systems": state.get("affected_systems"),
            "mitre_techniques": state.get("mitre_techniques"),
            "constraints_logged": state.get("constraints"),
            "generated_at": datetime.now().isoformat(),
            "fallback_flags": state.get("fallback_flags"),
        }

        with open(report_path, "w") as f:
            json.dump(full_report, f, indent=2, default=str)

        return report_path
    except Exception as e:
        logger.warning(f"Could not save report: {e}")
        return ""
