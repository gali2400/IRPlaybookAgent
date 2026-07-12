"""
IRPlaybookAgent — Streamlit UI
AI-powered adaptive incident response system for MedBridge Health Systems.

Usage:
    streamlit run app/streamlit_app.py

Features:
  - Natural language incident description input
  - Real-time triage classification and severity assessment
  - NIST 800-61 aligned playbook with MITRE ATT&CK mapping
  - Critic validation with blocking issue detection
  - Conversational advisor loop for follow-up questions and constraint handling
  - Post-incident report generation
"""
# Developed with AI assistance (Claude)

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

import streamlit as st

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / ".env")

# Streamlit Cloud secrets support
try:
    if "GEMINI_API_KEY" in st.secrets and not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    if "GROQ_API_KEY" in st.secrets and not os.environ.get("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except FileNotFoundError:
    pass

logger = logging.getLogger(__name__)

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IRPlaybookAgent — Incident Response",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1A1A2E 0%, #C81026 100%);
        padding: 20px 24px;
        border-radius: 8px;
        margin-bottom: 20px;
        color: white;
    }
    .severity-critical { background: #FFE5E5; border-left: 4px solid #C00000; padding: 10px 15px; border-radius: 4px; margin: 5px 0; }
    .severity-high { background: #FFF0E5; border-left: 4px solid #FF6B00; padding: 10px 15px; border-radius: 4px; margin: 5px 0; }
    .severity-medium { background: #FFFBE5; border-left: 4px solid #FFA500; padding: 10px 15px; border-radius: 4px; margin: 5px 0; }
    .severity-low { background: #E5FFE5; border-left: 4px solid #008000; padding: 10px 15px; border-radius: 4px; margin: 5px 0; }
    .phase-header { background: #1A3A5C; color: white; padding: 10px 15px; border-radius: 6px; margin: 15px 0 5px 0; }
    .warning-box { background: #FFF3CD; border-left: 4px solid #FF6B00; padding: 8px 12px; border-radius: 4px; margin: 5px 0; font-size: 0.9em; }
    .critic-blocking { background: #FFE5E5; border-left: 4px solid #C00000; padding: 8px 12px; border-radius: 4px; margin: 5px 0; }
    .critic-warning { background: #FFF0E5; border-left: 4px solid #FF6B00; padding: 8px 12px; border-radius: 4px; margin: 5px 0; }
    .chat-responder { background: #E8F0FE; padding: 10px 15px; border-radius: 8px; margin: 5px 0; }
    .chat-advisor { background: #F0F4F8; border-left: 3px solid #1A3A5C; padding: 10px 15px; border-radius: 8px; margin: 5px 0; }
    .immediate-action { background: #FFE5E5; border-left: 4px solid #C00000; padding: 8px 12px; border-radius: 4px; margin: 3px 0; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    _has_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    _has_groq = bool(os.environ.get("GROQ_API_KEY"))

    if _has_gemini or _has_groq:
        _llm_name = "Groq" if _has_groq else "Gemini 2.0 Flash"
        st.markdown(f"### ✅ LLM: {_llm_name}")
        st.success("API key loaded from .env")
    else:
        st.markdown("### ⚠️ LLM: Not Configured")
        st.error("No API key. Copy `.env.example` to `.env` and add GEMINI_API_KEY or GROQ_API_KEY.")

    st.markdown("---")
    st.markdown("### 🏥 Organization")
    try:
        from config.settings import ORG_NAME, ORG_INDUSTRY, ORG_PROFILE
        st.markdown(f"**{ORG_NAME}**")
        st.markdown(f"Industry: {ORG_INDUSTRY}")
        st.markdown(f"Frameworks: {', '.join(ORG_PROFILE.get('regulatory_frameworks', []))}")
    except Exception:
        st.markdown("MedBridge Health Systems")

    st.markdown("---")
    st.markdown("### 📖 How It Works")
    st.markdown("""
**IRPlaybookAgent** uses a 5-agent pipeline:

1. 🔍 **Triage Agent** — Classify incident type & severity
2. 📋 **Playbook Generator** — Build NIST 800-61 response plan
3. 🔎 **Critic Agent** — Validate for dangerous/missing steps
4. 💬 **Advisor Agent** — Answer questions, adapt in real time
5. 📄 **Documentation Agent** — Generate incident report

**Free stack:** Groq/Gemini + LangGraph + Streamlit
    """)

    st.markdown("---")
    st.markdown("### 💡 Demo Scenarios")
    demo_scenarios = {
        "🔴 Ransomware on Clinical Workstations": (
            "Ransomware detected on 3 Windows workstations in the cardiology unit at 2am. "
            "Files are actively encrypting. We're on hybrid Azure + on-premises with Epic EHR running."
        ),
        "🟠 Phishing / Credential Compromise": (
            "An accounts payable employee clicked a phishing link and entered their O365 credentials "
            "on a fake login page 20 minutes ago. We suspect AiTM — same as INC-2023-001."
        ),
        "🟡 Azure Blob Data Exposure": (
            "Unusual data egress from Azure Blob Storage container AZ-005 detected at 3am on a weekend. "
            "The container holds radiology DICOM images. Possible repeat of INC-2024-002."
        ),
    }
    selected_demo = st.selectbox("Load a demo scenario", ["(none)"] + list(demo_scenarios.keys()))

# ── Main Header ───────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🚨 IRPlaybookAgent</h1>
    <p>AI-Powered Adaptive Incident Response | MedBridge Health Systems | CIS 8045 Agentic AI</p>
</div>
""", unsafe_allow_html=True)

# ── Initialize Session State ──────────────────────────────────────────────────

if "pipeline_state" not in st.session_state:
    st.session_state.pipeline_state = None
if "pipeline_ran" not in st.session_state:
    st.session_state.pipeline_ran = False

# ── Incident Input ────────────────────────────────────────────────────────────

st.markdown("## 📝 Describe the Incident")
st.markdown("Describe what you're seeing in plain language. Include affected systems, what's happening, and when it started.")

default_text = demo_scenarios.get(selected_demo, "") if selected_demo != "(none)" else ""

incident_input = st.text_area(
    "Incident description",
    value=default_text,
    height=120,
    placeholder="e.g., Ransomware detected on 3 clinical workstations in cardiology at 2am. Files are actively encrypting...",
    label_visibility="collapsed",
)

col1, col2 = st.columns([1, 4])
with col1:
    _api_ready = _has_gemini or _has_groq
    run_button = st.button(
        "🚀 Run Triage + Playbook",
        type="primary",
        use_container_width=True,
        disabled=not _api_ready or not incident_input.strip(),
    )
with col2:
    if not _api_ready:
        st.warning("⚠️ Add API key to `.env` first")
    elif not incident_input.strip():
        st.info("Enter an incident description above to get started")
    else:
        st.info(f"✅ {_llm_name} ready — click Run to start the pipeline")

# ── Run Initial Pipeline ──────────────────────────────────────────────────────

if run_button and incident_input.strip():
    st.markdown("---")
    st.markdown("## ⚡ Running Pipeline")

    progress_bar = st.progress(0)
    status_text = st.empty()

    steps = ["Triage Agent", "Playbook Generator", "Critic Agent", "Human Review"]
    for i, step in enumerate(steps):
        status_text.markdown(f"🔄 **{step}** running...")
        progress_bar.progress((i + 1) * 22)

    try:
        with st.spinner("IRPlaybookAgent analyzing incident..."):
            from agents.graph import run_initial_pipeline
            state = run_initial_pipeline(
                incident_description=incident_input.strip(),
                approved=True,
            )
        progress_bar.progress(100)
        status_text.markdown("✅ **Pipeline complete**")
        st.session_state.pipeline_state = state
        st.session_state.pipeline_ran = True
        st.rerun()
    except Exception as e:
        st.error(f"❌ Pipeline error: {str(e)}")
        logger.exception("Pipeline failed")

# ── Results ───────────────────────────────────────────────────────────────────

if st.session_state.pipeline_ran and st.session_state.pipeline_state:
    state = st.session_state.pipeline_state

    # Show errors if any
    if state.get("errors"):
        with st.expander(f"⚠️ {len(state['errors'])} Warning(s)", expanded=False):
            for err in state["errors"]:
                st.warning(err)

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Triage", "📋 Playbook", "🔎 Critic Review", "💬 Advisor", "📄 Report"
    ])

    # ── Tab 1: Triage ─────────────────────────────────────────────────────────
    with tab1:
        severity = state.get("severity", "Unknown")
        severity_class = f"severity-{severity.lower()}" if severity in ("Critical", "High", "Medium", "Low") else ""

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Incident Type", state.get("incident_type", "Unknown").replace("_", " ").title())
        with col_b:
            st.metric("Severity", severity)
        with col_c:
            systems = state.get("affected_systems") or []
            st.metric("Systems Affected", len(systems))

        st.markdown("### Triage Summary")
        if severity_class:
            st.markdown(f'<div class="{severity_class}">{state.get("triage_summary", "")}</div>', unsafe_allow_html=True)
        else:
            st.info(state.get("triage_summary", ""))

        st.markdown("### Blast Radius")
        st.warning(state.get("blast_radius", "Undetermined"))

        st.markdown("### ⚡ Immediate Actions (Do These Now)")
        for action in (state.get("immediate_actions") or []):
            st.markdown(f'<div class="immediate-action">→ {action}</div>', unsafe_allow_html=True)

        st.markdown("### Affected Systems")
        for system in (state.get("affected_systems") or []):
            st.markdown(f"- {system}")

        st.markdown("### MITRE ATT&CK Techniques")
        mitre = state.get("mitre_techniques") or []
        if mitre:
            import pandas as pd
            df = pd.DataFrame([{
                "ID": t.get("id", ""),
                "Name": t.get("name", ""),
                "Tactic": t.get("tactic", ""),
                "Relevance": t.get("relevance", ""),
            } for t in mitre])
            st.dataframe(df, use_container_width=True)

    # ── Tab 2: Playbook ───────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Response Playbook")
        st.info(state.get("playbook_summary", ""))

        phases = state.get("revised_playbook_phases") or state.get("playbook_phases") or []
        if phases:
            for phase in phases:
                st.markdown(f'<div class="phase-header">📌 {phase.get("phase", "Phase")}</div>', unsafe_allow_html=True)
                st.caption(phase.get("description", ""))
                for step in phase.get("steps", []):
                    step_num = step.get("step_number", "")
                    with st.expander(f"Step {step_num}: {step.get('action', '')[:80]}", expanded=True):
                        col_x, col_y, col_z = st.columns(3)
                        with col_x:
                            st.markdown(f"**Who:** {step.get('who', '')}")
                        with col_y:
                            st.markdown(f"**Time:** {step.get('time_estimate', '')}")
                        with col_z:
                            st.markdown(f"**Rationale:** {step.get('rationale', '')}")
                        if step.get("warning"):
                            st.markdown(
                                f'<div class="warning-box">⚠️ <strong>Warning:</strong> {step["warning"]}</div>',
                                unsafe_allow_html=True
                            )
        else:
            st.warning("No playbook generated yet.")

    # ── Tab 3: Critic Review ──────────────────────────────────────────────────
    with tab3:
        st.markdown("### Critic / Validator Review")
        issues = state.get("critic_issues") or []
        approved = state.get("critic_approved", True)

        if approved and not issues:
            st.success("✅ Playbook passed review — no blocking issues found")
        elif approved:
            st.warning(f"⚠️ Playbook approved with {len(issues)} advisory notes")
        else:
            st.error(f"❌ Playbook has blocking issues — see below")

        blocking = [i for i in issues if i.get("severity") == "Blocking"]
        warnings = [i for i in issues if i.get("severity") == "Warning"]
        advisory = [i for i in issues if i.get("severity") == "Advisory"]

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("🔴 Blocking", len(blocking))
        with col_b:
            st.metric("🟠 Warnings", len(warnings))
        with col_c:
            st.metric("🟡 Advisory", len(advisory))

        for issue in issues:
            sev = issue.get("severity", "Advisory")
            css_class = "critic-blocking" if sev == "Blocking" else "critic-warning"
            icon = "🔴" if sev == "Blocking" else "🟠" if sev == "Warning" else "🟡"
            st.markdown(
                f'<div class="{css_class}">'
                f'{icon} <strong>{sev}</strong> — {issue.get("affected_step", "")}<br>'
                f'<strong>Issue:</strong> {issue.get("issue", "")}<br>'
                f'<strong>Fix:</strong> {issue.get("recommendation", "")}'
                f'</div>',
                unsafe_allow_html=True
            )

        if blocking:
            st.markdown("### Revised Playbook")
            st.success("The playbook above (Playbook tab) has been automatically revised to address blocking issues.")

    # ── Tab 4: Advisor ────────────────────────────────────────────────────────
    with tab4:
        st.markdown("### 💬 Ask the Advisor")
        st.markdown("Ask follow-up questions, report constraints, or update on progress. The advisor adapts the playbook in real time.")

        # Show conversation history
        history = state.get("conversation_history") or []
        if history:
            st.markdown("#### Conversation")
            for msg in history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                if role == "responder":
                    st.markdown(
                        f'<div class="chat-responder">🧑‍💻 <strong>You [{timestamp}]:</strong> {content}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="chat-advisor">🤖 <strong>Advisor [{timestamp}]:</strong> {content}</div>',
                        unsafe_allow_html=True
                    )

        # Constraints log
        constraints = state.get("constraints") or []
        if constraints:
            with st.expander(f"📌 Logged Constraints ({len(constraints)})", expanded=False):
                for c in constraints:
                    st.markdown(f"- {c}")

        # Input
        st.markdown("---")
        if state.get("session_complete"):
            st.success("✅ Session marked complete. Go to the Report tab to generate the incident report.")
        else:
            user_msg = st.text_input(
                "Your message",
                placeholder='e.g., "We can\'t take the Epic server offline" or "Step 3 is done, what\'s next?"',
                key="advisor_input",
            )
            col_send, col_done = st.columns([2, 1])
            with col_send:
                send_btn = st.button("Send →", type="primary", use_container_width=True)
            with col_done:
                done_btn = st.button("End Session & Generate Report", use_container_width=True)

            if send_btn and user_msg.strip():
                from agents.advisor_agent import run_advisor_turn
                updated_state = run_advisor_turn(state, user_msg.strip())
                st.session_state.pipeline_state = updated_state
                st.rerun()

            if done_btn:
                from agents.advisor_agent import run_advisor_turn
                updated_state = run_advisor_turn(state, "I'm done with the response. Please generate the incident report.")
                updated_state["session_complete"] = True
                st.session_state.pipeline_state = updated_state
                st.rerun()

    # ── Tab 5: Report ─────────────────────────────────────────────────────────
    with tab5:
        st.markdown("### 📄 Incident Report")

        if not state.get("session_complete"):
            st.info("Complete the advisor session first, then generate the report. Click 'End Session & Generate Report' in the Advisor tab.")
        elif not state.get("report_path"):
            if st.button("📄 Generate Incident Report", type="primary"):
                with st.spinner("Documentation Agent generating report..."):
                    from agents.documentation_agent import run_documentation_node
                    updated_state = run_documentation_node(state)
                    st.session_state.pipeline_state = updated_state
                    st.rerun()
        else:
            report_path = state.get("report_path", "")
            st.success(f"✅ Report generated: `{os.path.basename(report_path)}`")

            # Display report contents
            try:
                with open(report_path, "r") as f:
                    report_data = json.load(f)

                st.markdown("#### Executive Summary")
                st.info(report_data.get("executive_summary", ""))

                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.markdown("#### Incident Timeline")
                    for event in (report_data.get("incident_timeline") or []):
                        st.markdown(f"**{event.get('timestamp', '')}** — {event.get('event', '')} *(by {event.get('actor', '')})*")

                with col_r2:
                    st.markdown("#### Lessons Learned")
                    for lesson in (report_data.get("lessons_learned") or []):
                        st.markdown(f"- {lesson}")

                # HIPAA Assessment
                hipaa = report_data.get("hipaa_assessment") or {}
                if hipaa:
                    st.markdown("#### HIPAA Breach Assessment")
                    phi = hipaa.get("phi_involved", False)
                    breach = hipaa.get("breach_determination", "")
                    if phi:
                        st.error(f"⚠️ PHI Involved: {breach}")
                    else:
                        st.success(f"✅ PHI Assessment: {breach}")
                    st.markdown(f"**Notification Required:** {'Yes' if hipaa.get('notification_required') else 'No'}")
                    if hipaa.get("notification_deadline"):
                        st.markdown(f"**Deadline:** {hipaa.get('notification_deadline')}")
                    for entity in (hipaa.get("entities_to_notify") or []):
                        st.markdown(f"- Notify: {entity}")

                st.markdown("#### Recommendations")
                for rec in (report_data.get("recommendations") or []):
                    st.markdown(f"- {rec}")

            except Exception as e:
                st.warning(f"Could not display report contents: {e}")

            # Download raw JSON
            try:
                with open(report_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Full Report (.json)",
                        data=f.read(),
                        file_name=os.path.basename(report_path),
                        mime="application/json",
                    )
            except Exception:
                pass

# ── Reset ─────────────────────────────────────────────────────────────────────

if st.session_state.pipeline_ran:
    st.markdown("---")
    if st.button("🔄 Start New Incident"):
        st.session_state.pipeline_state = None
        st.session_state.pipeline_ran = False
        st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<small>IRPlaybookAgent | CIS 8045 Agentic AI | Georgia State University | "
    "Powered by LangGraph + Groq (free tier) | NIST SP 800-61 + MITRE ATT&CK</small>",
    unsafe_allow_html=True,
)
