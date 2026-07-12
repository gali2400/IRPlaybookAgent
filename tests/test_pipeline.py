"""
Integration tests for the IRPlaybookAgent pipeline.
Tests the full triage → playbook → critic flow using fallback (no LLM required).

Run with: pytest tests/ -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.triage_agent import _apply_fallback
from agents.playbook_agent import _apply_fallback as playbook_fallback, _get_generic_playbook
from agents.critic_agent import _parse_review


def _base_state() -> dict:
    return {
        "incident_description": "Ransomware detected on 3 clinical workstations.",
        "org_name": "MedBridge Health Systems",
        "org_context": "Healthcare org, Epic EHR, no SIEM, no EDR, 35% MFA",
        "incident_type": "ransomware",
        "severity": "Critical",
        "affected_systems": ["Cardiology Workstations", "Epic EHR"],
        "blast_radius": "Could spread to all endpoints via AD.",
        "mitre_techniques": [{"id": "T1486", "name": "Data Encrypted for Impact", "tactic": "Impact", "relevance": "Active encryption"}],
        "immediate_actions": ["Isolate workstations", "Notify IT Director"],
        "triage_summary": "Active ransomware. Critical.",
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
        "current_step": "triage",
        "approved": True,
        "errors": [],
        "progress_messages": [],
        "fallback_flags": {},
    }


class TestPlaybookFallback:
    def test_generic_playbook_has_4_phases(self):
        phases = _get_generic_playbook("ransomware")
        assert len(phases) == 4

    def test_phases_have_steps(self):
        phases = _get_generic_playbook("ransomware")
        for phase in phases:
            assert len(phase.get("steps", [])) > 0

    def test_steps_have_required_fields(self):
        phases = _get_generic_playbook("phishing")
        for phase in phases:
            for step in phase.get("steps", []):
                assert "action" in step
                assert "rationale" in step
                assert "who" in step
                assert "time_estimate" in step

    def test_playbook_fallback_applies_correctly(self):
        state = _base_state()
        playbook_fallback(state)
        assert state["playbook_phases"] is not None
        assert len(state["playbook_phases"]) == 4
        assert state["fallback_flags"]["playbook"] == "fallback_static"

    def test_phase_1_is_containment(self):
        phases = _get_generic_playbook("ransomware")
        assert "Containment" in phases[0]["phase"]

    def test_phase_4_is_post_incident(self):
        phases = _get_generic_playbook("ransomware")
        assert "Post-Incident" in phases[3]["phase"]

    def test_phase_4_includes_hipaa_step(self):
        phases = _get_generic_playbook("ransomware")
        post_incident_actions = " ".join(
            step["action"] for step in phases[3].get("steps", [])
        )
        assert "HIPAA" in post_incident_actions


class TestCriticParsing:
    def test_parse_no_issues(self):
        content = '{"issues": [], "approved": true, "revised_notes": "Looks good."}'
        result = _parse_review(content)
        assert result["approved"] is True
        assert result["issues"] == []

    def test_parse_blocking_issue(self):
        content = """{
            "issues": [{"issue": "Step suggests wiping before forensics", "severity": "Blocking",
                        "affected_step": "Phase 2, Step 1", "recommendation": "Image the drive first"}],
            "approved": false,
            "revised_notes": "Fix forensics order."
        }"""
        result = _parse_review(content)
        assert result["approved"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["severity"] == "Blocking"

    def test_parse_with_markdown_fence(self):
        content = '```json\n{"issues": [], "approved": true, "revised_notes": ""}\n```'
        result = _parse_review(content)
        assert result["approved"] is True

    def test_parse_invalid_returns_default(self):
        result = _parse_review("not valid json")
        assert result["approved"] is True
        assert result["issues"] == []


class TestStateStructure:
    def test_base_state_has_required_keys(self):
        state = _base_state()
        required = [
            "incident_description", "org_name", "org_context",
            "incident_type", "severity", "affected_systems",
            "playbook_phases", "critic_issues", "conversation_history",
            "constraints", "errors", "progress_messages", "fallback_flags"
        ]
        for key in required:
            assert key in state, f"Missing required state key: {key}"

    def test_errors_starts_empty(self):
        state = _base_state()
        assert state["errors"] == []

    def test_constraints_starts_empty(self):
        state = _base_state()
        assert state["constraints"] == []

    def test_conversation_history_starts_empty(self):
        state = _base_state()
        assert state["conversation_history"] == []
