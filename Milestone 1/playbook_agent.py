"""
Agent 2: Playbook Generator
Produces a structured, NIST SP 800-61 aligned incident response playbook
based on the triage classification and org context.

NIST SP 800-61 Phases:
  Phase 1: Immediate Containment  (stop the bleeding)
  Phase 2: Eradication            (remove the threat)
  Phase 3: Recovery               (restore operations safely)
  Phase 4: Post-Incident Activity (document, learn, improve)
"""
# Developed with AI assistance (Claude)

import json
import logging
from langchain_core.messages import HumanMessage

from config.settings import get_llm, ORG_NAME
from agents.state import AgentState

logger = logging.getLogger(__name__)

PLAYBOOK_PROMPT = """You are a senior incident response consultant generating a step-by-step response playbook for {org_name}.

Organization context:
{org_context}

Incident triage results:
- Incident Type: {incident_type}
- Severity: {severity}
- Affected Systems: {affected_systems}
- Blast Radius: {blast_radius}
- MITRE Techniques: {mitre_techniques}
- Triage Summary: {triage_summary}

Generate a detailed incident response playbook aligned to NIST SP 800-61, organized into 4 phases.

For each phase, provide 4-7 specific, actionable steps. Each step must include:
- action: What exactly to do (specific, not vague)
- rationale: Why this step matters for this specific incident
- who: Who should perform this (e.g., "IT Director", "sysadmin", "CISO", "legal counsel")
- time_estimate: How long this step takes (e.g., "5 minutes", "1-2 hours")
- warning: Any dangerous side effect to be aware of (null if none). Examples:
  - "Disabling this account will also lock out active nurses using Epic EHR"
  - "Powering off before imaging destroys volatile memory evidence"
  - "Notifying the vendor before forensics are complete may alert an insider"

Phases:
1. Immediate Containment — Stop the threat from spreading. Time-critical. Do these first.
2. Eradication — Remove the attacker's foothold, malware, or unauthorized access completely.
3. Recovery — Restore affected systems safely, verify integrity before bringing back online.
4. Post-Incident Activity — Document, report, notify (HIPAA if applicable), and improve.

Be extremely specific to this organization's environment. Reference Epic EHR, Azure AD, the LabConnect VPN,
the Cisco ASA firewall, or specific gaps (no EDR, no SIEM) where relevant.

For healthcare organizations, include HIPAA breach notification steps in Phase 4 if PHI may be involved.

Return a JSON object:
{{
  "playbook_phases": [
    {{
      "phase": "Phase 1: Immediate Containment",
      "description": "Stop active threat spread — complete within first 30 minutes",
      "steps": [
        {{
          "step_number": 1,
          "action": "...",
          "rationale": "...",
          "who": "...",
          "time_estimate": "...",
          "warning": null
        }}
      ]
    }}
  ],
  "playbook_summary": "2-3 sentence overview of the response strategy"
}}

Return only valid JSON:"""


def run_playbook_node(state: AgentState) -> AgentState:
    """LangGraph node for the Playbook Generator Agent."""
    logger.info("Playbook Agent: Generating response playbook")
    state["current_step"] = "playbook_generation"
    state["progress_messages"] = state.get("progress_messages", [])
    state["progress_messages"].append("Playbook Agent: Building response playbook...")

    try:
        llm = get_llm()
        mitre_str = json.dumps(state.get("mitre_techniques", []), indent=2)
        prompt = PLAYBOOK_PROMPT.format(
            org_name=state.get("org_name", ORG_NAME),
            org_context=state.get("org_context", ""),
            incident_type=state.get("incident_type", "unknown"),
            severity=state.get("severity", "High"),
            affected_systems=", ".join(state.get("affected_systems", [])),
            blast_radius=state.get("blast_radius", ""),
            mitre_techniques=mitre_str,
            triage_summary=state.get("triage_summary", ""),
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        playbook_data = _parse_playbook(response.content)

        state["playbook_phases"] = playbook_data.get("playbook_phases", [])
        state["playbook_summary"] = playbook_data.get("playbook_summary", "")
        # Initialize revised playbook as same as original
        state["revised_playbook_phases"] = state["playbook_phases"]

        fallback_flags = state.get("fallback_flags") or {}
        fallback_flags["playbook"] = "llm_generated"
        state["fallback_flags"] = fallback_flags

        step_count = sum(len(p.get("steps", [])) for p in state["playbook_phases"])
        state["progress_messages"].append(f"Playbook Agent: Generated {step_count} steps across 4 phases ✓")
        logger.info(f"Playbook complete: {step_count} steps across {len(state['playbook_phases'])} phases")

    except Exception as e:
        logger.error(f"Playbook Agent error: {e}")
        state["errors"] = state.get("errors", []) + [f"Playbook Agent: {str(e)}"]
        _apply_fallback(state)

    return state


def _parse_playbook(content: str) -> dict:
    """Parse JSON playbook from LLM response."""
    try:
        content = content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            # Ensure step_number is set
            for phase in data.get("playbook_phases", []):
                for i, step in enumerate(phase.get("steps", []), 1):
                    step.setdefault("step_number", i)
                    step.setdefault("warning", None)
            return data
    except Exception as e:
        logger.warning(f"Playbook JSON parse failed: {e}")
    return {}


def _apply_fallback(state: AgentState) -> None:
    """Apply generic NIST 800-61 fallback playbook when LLM fails."""
    incident_type = state.get("incident_type", "unknown")
    state["playbook_phases"] = state.get("playbook_phases") or _get_generic_playbook(incident_type)
    state["revised_playbook_phases"] = state["playbook_phases"]
    state["playbook_summary"] = state.get("playbook_summary") or (
        "Generic NIST 800-61 playbook applied. "
        "Adapt steps to your specific environment and incident details."
    )
    fallback_flags = state.get("fallback_flags") or {}
    fallback_flags["playbook"] = "fallback_static"
    state["fallback_flags"] = fallback_flags


def _get_generic_playbook(incident_type: str) -> list[dict]:
    """Generic NIST 800-61 playbook as fallback."""
    return [
        {
            "phase": "Phase 1: Immediate Containment",
            "description": "Stop the active threat from spreading — complete within first 30 minutes",
            "steps": [
                {"step_number": 1, "action": "Isolate affected systems from the network (disconnect switch port or disable NIC)", "rationale": "Prevents lateral movement", "who": "IT Administrator", "time_estimate": "5 minutes", "warning": "Verify no critical services will be disrupted before isolating"},
                {"step_number": 2, "action": "Preserve volatile memory — take a memory dump before any reboots", "rationale": "RAM contains attacker tools, credentials, and encryption keys that are lost on reboot", "who": "IT Administrator", "time_estimate": "15-30 minutes", "warning": "Do NOT power off the system before capturing memory"},
                {"step_number": 3, "action": "Disable compromised user accounts in Active Directory", "rationale": "Cuts off attacker's access path", "who": "IT Administrator", "time_estimate": "5 minutes", "warning": "Verify account is not a shared account used by other active users"},
                {"step_number": 4, "action": "Revoke active sessions for compromised accounts (Azure AD sign-out all)", "rationale": "Invalidates any active tokens even if password is changed", "who": "IT Administrator", "time_estimate": "5 minutes", "warning": None},
                {"step_number": 5, "action": "Notify IT Director and document incident start time", "rationale": "Starts the official incident clock — critical for HIPAA 60-day notification window", "who": "First responder", "time_estimate": "2 minutes", "warning": None},
            ]
        },
        {
            "phase": "Phase 2: Eradication",
            "description": "Remove the attacker's foothold and malware completely",
            "steps": [
                {"step_number": 1, "action": "Run full antivirus/EDR scan on all affected and adjacent systems", "rationale": "Identifies malware, backdoors, and persistence mechanisms", "who": "IT Administrator", "time_estimate": "1-4 hours", "warning": None},
                {"step_number": 2, "action": "Review and remove unauthorized accounts, scheduled tasks, registry run keys, and startup items", "rationale": "Attackers commonly establish persistence via these mechanisms", "who": "IT Administrator", "time_estimate": "1-2 hours", "warning": None},
                {"step_number": 3, "action": "Reset passwords for all compromised and potentially exposed accounts", "rationale": "Ensures attacker cannot reuse stolen credentials", "who": "IT Administrator", "time_estimate": "30 minutes", "warning": "Use a secure out-of-band channel to distribute new passwords"},
                {"step_number": 4, "action": "Patch the vulnerability or close the attack vector that was exploited", "rationale": "Prevents reinfection through the same entry point", "who": "IT Administrator", "time_estimate": "Varies", "warning": None},
            ]
        },
        {
            "phase": "Phase 3: Recovery",
            "description": "Restore systems safely and verify integrity before returning to production",
            "steps": [
                {"step_number": 1, "action": "Restore from clean backup — verify backup integrity before restoring", "rationale": "Ensures restored system does not contain malware", "who": "IT Administrator", "time_estimate": "2-8 hours", "warning": "Verify the backup predates the compromise — do not restore from infected backup"},
                {"step_number": 2, "action": "Rebuild compromised systems from known-good images where feasible", "rationale": "More reliable than attempting to clean a compromised system", "who": "IT Administrator", "time_estimate": "4-24 hours", "warning": None},
                {"step_number": 3, "action": "Monitor restored systems closely for 72 hours post-recovery", "rationale": "Detects reinfection or missed persistence mechanisms", "who": "IT Administrator", "time_estimate": "72 hours ongoing", "warning": None},
                {"step_number": 4, "action": "Verify application and data integrity before returning to production", "rationale": "Ensures data was not tampered with during the incident", "who": "IT Director / Application Owner", "time_estimate": "1-4 hours", "warning": None},
            ]
        },
        {
            "phase": "Phase 4: Post-Incident Activity",
            "description": "Document, report, notify, and improve",
            "steps": [
                {"step_number": 1, "action": "Complete incident timeline documentation — every action with timestamp", "rationale": "Required for regulatory reporting and forensic records", "who": "IT Director", "time_estimate": "2-4 hours", "warning": None},
                {"step_number": 2, "action": "Conduct HIPAA breach risk assessment — determine if PHI was accessed or exfiltrated", "rationale": "HIPAA requires notification within 60 days of discovering a breach", "who": "HIPAA Security Officer / Legal", "time_estimate": "4-8 hours", "warning": None},
                {"step_number": 3, "action": "Report to HHS if PHI breach is confirmed and affects 500+ individuals", "rationale": "HIPAA Breach Notification Rule requirement", "who": "HIPAA Security Officer / Legal", "time_estimate": "1-2 hours", "warning": None},
                {"step_number": 4, "action": "Conduct post-incident lessons learned meeting within 2 weeks", "rationale": "Identifies process improvements and gaps to close", "who": "IT Director, HIPAA Officer, affected stakeholders", "time_estimate": "2 hours", "warning": None},
                {"step_number": 5, "action": "Update Incident Response Plan with findings from this incident", "rationale": "Improves future response capability", "who": "IT Director", "time_estimate": "4-8 hours", "warning": None},
            ]
        }
    ]
