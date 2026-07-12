"""
LangGraph Agent State Schema
Defines the shared state TypedDict that flows through all agents in the IRPlaybookAgent pipeline.
"""
# Developed with AI assistance (Claude)

from typing import Optional
from typing_extensions import TypedDict
# Developed with AI assistance (Claude)  

class AgentState(TypedDict):
    """
    Shared state passed between all agents in the LangGraph pipeline.
    Each agent reads from and writes to this state.
    """

    # ── Input ──────────────────────────────────────────────────────────────────
    incident_description: str           # Raw incident description from the user
    org_name: str                       # Organization name (from org_profile.json)
    org_context: str                    # Full org context string for agent prompts

    # ── Agent 1: Triage Output ─────────────────────────────────────────────────
    incident_type: Optional[str]        # "ransomware" | "phishing" | "insider_threat" |
                                        # "data_breach" | "cloud_misconfiguration" |
                                        # "malware" | "ddos" | "credential_compromise" | "unknown"
    severity: Optional[str]             # "Critical" | "High" | "Medium" | "Low"
    affected_systems: Optional[list[str]]   # List of impacted systems/assets
    blast_radius: Optional[str]         # Description of potential spread
    mitre_techniques: Optional[list[dict]]  # [{id, name, tactic, relevance}]
    immediate_actions: Optional[list[str]]  # Things to do RIGHT NOW before full playbook
    triage_summary: Optional[str]       # Short summary of the incident classification

    # ── Agent 2: Playbook Generator Output ────────────────────────────────────
    playbook_phases: Optional[list[dict]]   # NIST 800-61 phases with steps
                                            # [{phase, description, steps: [{action, rationale,
                                            #   who, time_estimate, warning}]}]
    playbook_summary: Optional[str]     # Short summary of the overall response plan

    # ── Agent 3: Critic / Validator Output ────────────────────────────────────
    critic_issues: Optional[list[dict]]     # [{issue, severity, recommendation}]
    critic_approved: Optional[bool]         # True if playbook passed review
    revised_playbook_phases: Optional[list[dict]]   # Updated playbook after critic revisions

    # ── Advisor Loop (Conversational) ─────────────────────────────────────────
    conversation_history: Optional[list[dict]]  # [{role, content, timestamp}]
    constraints: Optional[list[str]]            # Logged constraints from user (e.g., "can't take Epic offline")
    advisor_response: Optional[str]             # Latest advisor response
    session_complete: Optional[bool]            # True when user ends the session

    # ── Agent 5: Documentation Output ─────────────────────────────────────────
    incident_timeline: Optional[list[dict]]     # [{timestamp, event, actor}]
    lessons_learned: Optional[list[str]]
    hipaa_assessment: Optional[dict]            # Breach notification determination
    report_path: Optional[str]                  # Path to generated incident report

    # ── Pipeline Control ────────────────────────────────────────────────────────
    current_step: str                   # Current pipeline step
    approved: Optional[bool]            # Human-in-the-loop approval flag
    errors: list[str]                   # Error messages from any agent
    progress_messages: list[str]        # Status messages for Streamlit UI
    fallback_flags: Optional[dict]      # {"agent_name": "llm_generated" | "fallback_static"}
