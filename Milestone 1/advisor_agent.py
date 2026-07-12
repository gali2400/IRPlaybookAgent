"""
Agent 4: Advisor Agent (Conversational Loop)
Handles the interactive phase of incident response — answering follow-up questions,
adapting the playbook when the responder reports constraints, and tracking what's been done.

This is the core agentic loop that differentiates IRPlaybookAgent from a static tool.
The advisor maintains conversation history and updates the playbook in real time.
"""
# Developed with AI assistance (Claude)
import json
import logging
from datetime import datetime
from langchain_core.messages import HumanMessage

from config.settings import get_llm, ORG_NAME
from agents.state import AgentState

logger = logging.getLogger(__name__)

ADVISOR_PROMPT = """You are an expert incident response advisor actively supporting a responder at {org_name}
during a live security incident. You must give direct, specific, actionable advice.

Organization context:
{org_context}

Current incident:
- Type: {incident_type}
- Severity: {severity}
- Affected Systems: {affected_systems}

Current playbook (already validated):
{playbook_json}

Known constraints the responder has reported so far:
{constraints}

Conversation history:
{conversation_history}

Responder's latest message:
\"\"\"{user_message}\"\"\"

Respond as an expert advisor:
1. If the responder is reporting a CONSTRAINT (e.g., "we can't take that server offline", "we don't have EDR"):
   - Acknowledge the constraint explicitly
   - Provide an ALTERNATIVE approach that achieves the same goal without the blocked action
   - Add the constraint to your mental model for future advice

2. If the responder is asking a QUESTION:
   - Answer directly and specifically
   - Reference the org context and known gaps where relevant
   - Give your best recommendation, not a generic answer

3. If the responder is REPORTING PROGRESS (e.g., "we isolated the server"):
   - Confirm the action was correct
   - Tell them what to do next based on the playbook

4. If the responder says they are DONE or wants to generate a report:
   - Summarize what was accomplished
   - Note any incomplete steps
   - Confirm you'll generate the incident report

Be direct. This is a live incident — no preamble, no disclaimers, just clear guidance.
Responses should be concise (3-8 sentences or a short bulleted list). No walls of text.

Also return whether any playbook steps need to be updated based on this interaction.

Return JSON:
{{
  "response": "Your advisor response here",
  "constraint_logged": "Description of constraint if one was reported, null otherwise",
  "session_complete": false,
  "playbook_update": null
}}

Return only valid JSON:"""


def run_advisor_turn(state: AgentState, user_message: str) -> AgentState:
    """
    Run a single advisor conversation turn.
    Called by Streamlit for each user follow-up message.
    Not a LangGraph node — called directly for the conversational loop.
    """
    logger.info(f"Advisor Agent: Processing user message")

    try:
        llm = get_llm()

        # Build conversation history string
        history = state.get("conversation_history") or []
        history_str = _format_history(history)

        # Build constraints string
        constraints = state.get("constraints") or []
        constraints_str = "\n".join(f"- {c}" for c in constraints) if constraints else "None reported yet"

        # Use revised playbook if available
        playbook = state.get("revised_playbook_phases") or state.get("playbook_phases") or []
        playbook_json = json.dumps(playbook, indent=2)

        prompt = ADVISOR_PROMPT.format(
            org_name=state.get("org_name", ORG_NAME),
            org_context=state.get("org_context", ""),
            incident_type=state.get("incident_type", "unknown"),
            severity=state.get("severity", "High"),
            affected_systems=", ".join(state.get("affected_systems", [])),
            playbook_json=playbook_json,
            constraints=constraints_str,
            conversation_history=history_str,
            user_message=user_message,
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        advisor_data = _parse_advisor_response(response.content)

        advisor_text = advisor_data.get("response", response.content)
        state["advisor_response"] = advisor_text

        # Log constraint if reported
        constraint = advisor_data.get("constraint_logged")
        if constraint:
            constraints = state.get("constraints") or []
            constraints.append(constraint)
            state["constraints"] = constraints
            logger.info(f"Constraint logged: {constraint}")

        # Check if session is complete
        state["session_complete"] = advisor_data.get("session_complete", False)

        # Update conversation history
        timestamp = datetime.now().strftime("%H:%M:%S")
        history = state.get("conversation_history") or []
        history.append({"role": "responder", "content": user_message, "timestamp": timestamp})
        history.append({"role": "advisor", "content": advisor_text, "timestamp": timestamp})
        state["conversation_history"] = history

        logger.info(f"Advisor turn complete. Session complete: {state['session_complete']}")

    except Exception as e:
        logger.error(f"Advisor Agent error: {e}")
        state["errors"] = state.get("errors", []) + [f"Advisor Agent: {str(e)}"]
        state["advisor_response"] = (
            "I encountered an error processing your message. "
            "Please continue following the playbook and try again."
        )

        # Still log to conversation history
        timestamp = datetime.now().strftime("%H:%M:%S")
        history = state.get("conversation_history") or []
        history.append({"role": "responder", "content": user_message, "timestamp": timestamp})
        history.append({"role": "advisor", "content": state["advisor_response"], "timestamp": timestamp})
        state["conversation_history"] = history

    return state


def _format_history(history: list[dict]) -> str:
    """Format conversation history for the prompt."""
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-10:]:  # Last 10 messages to avoid context overflow
        role = "Responder" if msg["role"] == "responder" else "Advisor"
        lines.append(f"[{msg.get('timestamp', '')}] {role}: {msg['content']}")
    return "\n".join(lines)


def _parse_advisor_response(content: str) -> dict:
    """Parse JSON from advisor response."""
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
        logger.warning(f"Advisor response parse failed: {e} — using raw text")
    return {"response": content, "constraint_logged": None, "session_complete": False}
