# IRPlaybookAgent

### AI-Powered Adaptive Incident Response System

**CIS 8045 Agentic AI | Georgia State University | Summer 2026**

---

IRPlaybookAgent is a conversational agentic AI system that guides security responders through live incidents in real time. It ingests a natural language incident description and runs a 5-agent LangGraph pipeline to classify the incident, generate a NIST SP 800-61 aligned response playbook, validate it for dangerous steps, and then adapts the plan interactively as the responder reports back constraints and progress.

**Simulated Organization:** MedBridge Health Systems (1,200-employee healthcare org, hybrid Azure + on-premises, Epic EHR, HIPAA-regulated)

---

## UI Screenshots

### Home — Incident Input
A non-technical responder describes the incident in plain language. The sidebar shows the active LLM, organization profile, a step-by-step explanation of the pipeline, and pre-loaded demo scenarios.

![Home screen — empty input](docs/screenshots/01_home_empty.png)

![Home screen — incident loaded and ready to run](docs/screenshots/02_home_loaded.png)

---

### Tab 1 — Triage Results
After running the pipeline, the Triage tab displays the incident type, severity, blast radius, immediate actions the responder should take right now, affected systems, and a MITRE ATT&CK technique table.

![Triage tab — ransomware classification](docs/screenshots/03_triage.png)

---

### Tab 2 — Response Playbook
The Playbook tab shows the NIST SP 800-61 aligned four-phase response plan (Containment → Eradication → Recovery → Post-Incident). Each step is expandable and shows who is responsible, time estimate, and rationale.

![Playbook tab — Phase 1 Containment and Phase 2 Eradication](docs/screenshots/04_playbook_phases1.png)

![Playbook tab — Phase 2 Eradication and Phase 3 Recovery](docs/screenshots/05_playbook_phases2.png)

![Playbook tab — Phase 4 Post-Incident Activity](docs/screenshots/06_playbook_phase4.png)

---

### Tab 3 — Critic / Validator Review
The Critic Agent reviews the generated playbook for dangerous or missing steps before it is delivered to the responder. Issues are classified as Blocking, Warning, or Advisory with specific fix recommendations.

![Critic Review tab — blocking issues and warnings](docs/screenshots/07_critic_review.png)

---

### Tab 4 — Advisor
The Advisor tab provides a conversational interface for follow-up questions, constraint reporting ("we can't take Epic offline"), and progress updates. The advisor adapts the playbook in real time.

![Advisor tab — chat interface](docs/screenshots/08_advisor.png)

---

### Tab 5 — Incident Report
After the advisor session ends, the Documentation Agent generates a structured incident report with executive summary, incident timeline, lessons learned, HIPAA breach assessment with notification deadlines, and recommendations.

![Report tab — executive summary, timeline, lessons learned](docs/screenshots/09_report_summary.png)

![Report tab — HIPAA breach assessment and recommendations](docs/screenshots/10_report_hipaa.png)

---

---

## Quick Start (All Free)

### 1. Get a Free API Key

- **Gemini** (primary): [aistudio.google.com](https://aistudio.google.com) — free tier: 15 req/min, no credit card
- **Groq** (alternative): [console.groq.com](https://console.groq.com) — free tier: 14,400 req/day

### 2. Setup

```bash
git clone <repo-url>
cd irplaybookagent
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY or GROQ_API_KEY
```

### 3. Download Framework Data

```bash
python scripts/download_frameworks.py
```

### 4. Run

```bash
streamlit run app/streamlit_app.py
```

### 5. Run Tests

```bash
pytest tests/ -v
```

---

## Architecture

```
Incident Description (user input)
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              LangGraph State Machine                │
│                                                     │
│  [1] Triage → [2] Playbook Generator → [3] Critic  │
│         → [4] Advisor Loop ↺ → [5] Documentation   │
└─────────────────────────────────────────────────────┘
```

| Agent | Purpose |
|---|---|
| **Triage Agent** | Classifies incident type, severity, affected systems, blast radius, MITRE techniques |
| **Playbook Generator** | Produces NIST SP 800-61 aligned containment → eradication → recovery plan |
| **Critic / Validator** | Reviews playbook for dangerous steps and missing critical actions before delivery |
| **Advisor Agent** | Conversational loop — answers follow-ups, adapts playbook to reported constraints |
| **Documentation Agent** | Generates formal incident report with HIPAA breach assessment |

---

## Key Features

- **NIST SP 800-61 Aligned:** All playbooks follow the standard IR lifecycle phases
- **MITRE ATT&CK Mapping:** Triage maps incident to relevant adversary techniques
- **Critic Validation:** Catches dangerous steps (e.g., wipe before forensics) before delivery
- **Adaptive Advisor Loop:** Replans in real time when responder reports constraints
- **HIPAA Breach Assessment:** Auto-generates notification checklist for healthcare incidents
- **MedBridge Context:** Org-specific guidance referencing actual systems, gaps, and prior incidents
- **Data Provenance:** Tracks whether each output was LLM-generated or fallback-static

---

## Free Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| LLM | Google Gemini 2.0 Flash (or Groq Llama 3.1) | Free |
| Agent Framework | LangGraph | Open source |
| Frontend | Streamlit | Open source |
| Testing | pytest | Open source |

---

## Project Structure

```
irplaybookagent/
├── agents/
│   ├── state.py                # LangGraph shared state schema
│   ├── graph.py                # Pipeline orchestration
│   ├── triage_agent.py         # Incident classification
│   ├── playbook_agent.py       # NIST 800-61 playbook generation
│   ├── critic_agent.py         # Playbook validation
│   ├── advisor_agent.py        # Conversational advisor loop
│   └── documentation_agent.py # Post-incident report generation
├── app/
│   └── streamlit_app.py        # Web UI
├── config/
│   ├── settings.py             # LLM config and paths
│   └── org_profile.json        # MedBridge organization profile
├── corpus/
│   └── medbridge_context.md    # MedBridge security context
├── data/frameworks/            # MITRE ATT&CK, NIST 800-61 (downloaded)
├── output/                     # Generated incident reports
├── scripts/
│   └── download_frameworks.py  # Framework data setup
├── tests/
│   ├── test_triage.py
│   └── test_pipeline.py
├── .env.example
├── requirements.txt
└── run_app.sh
```
