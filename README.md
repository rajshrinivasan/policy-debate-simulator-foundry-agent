# Project 04 — Policy Debate Simulator

## Pattern
**Hierarchical Multi-Agent — adversarial (ConnectedAgentTool)**

Four agents work together in a structured hierarchy. Three specialist agents
are created independently, then wrapped as `ConnectedAgentTool` objects and
given to a conductor. The conductor owns the conversation thread, calls each
specialist in sequence, and assembles the final output. The specialists never
talk to each other — they only respond to the conductor.

The adversarial twist: two of the three specialists are explicitly in conflict.
Connected agents are normally used for cooperative task delegation. Here they
are used to produce structured disagreement — a different use of the same pattern.

---

## Architecture

```
User (CLI)
    │
    ▼
agent.py  — AgentsClient (azure-ai-agents SDK)
    │
    │  1. Create 3 specialist agents (proponent, opponent, judge)
    │  2. Wrap each as a ConnectedAgentTool
    │  3. Create conductor agent with all 3 tools
    │  4. Create a thread per debate
    │
    │  ── per debate ─────────────────────────────────────────────────
    │  5. Add policy statement to thread as USER message
    │  6. runs.create_and_process(thread, conductor)
    │        │
    │        ├─► conductor calls proponent_agent("policy")
    │        │       └─► returns: 3-point argument FOR
    │        │
    │        ├─► conductor calls opponent_agent("policy")
    │        │       └─► returns: 3-point argument AGAINST
    │        │
    │        └─► conductor calls judge_agent("policy + both arguments")
    │                └─► returns: scores (Logic/Evidence/Persuasion) + verdict
    │
    │  7. messages.list() → extract conductor's assembled transcript
    └─────────────────────────────────────────────────────────────────
```

---

## The four agents

| Agent | Role | Prompt file |
|---|---|---|
| `proponent_agent` | Argues FOR the policy — 3 evidence-based points + pre-emptive rebuttal | `proponent_prompt.txt` |
| `opponent_agent` | Argues AGAINST — 3 counter-arguments + pre-emptive rebuttal | `opponent_prompt.txt` |
| `judge_agent` | Scores both sides: Logic, Evidence, Persuasion (each /10) + verdict | `judge_prompt.txt` |
| `debate_conductor` | Orchestrates the sequence, assembles transcript | `conductor_prompt.txt` |

---

## SDK difference from Projects 01–03

Projects 01–03 used `azure-ai-projects` with the **Responses API** (stateless,
request/response style). This project uses `azure-ai-agents` with the **Assistants
thread/run model**:

| Concept | azure-ai-projects (Responses API) | azure-ai-agents (Thread/Run) |
|---|---|---|
| Session | `conversations.create()` | `threads.create()` |
| Send message | `conversations.items.create()` | `messages.create()` |
| Run agent | `responses.create()` | `runs.create_and_process()` |
| Read reply | `response.output_text` | `messages.list()` |
| Sub-agents | Not applicable | `ConnectedAgentTool` |

`runs.create_and_process()` is a blocking call — it polls until the run
completes (including all sub-agent calls) and returns the finished state.

---

## Sample policy statements

| Policy | What makes it interesting to debate |
|---|---|
| Governments should ban single-use plastics entirely | Environment vs economic impact |
| University education should be free for all citizens | Equity vs fiscal sustainability |
| Social media platforms should be regulated as public utilities | Free speech vs consumer protection |
| Autonomous vehicles should be permitted on all public roads | Innovation vs safety liability |
| Remote work should be a legal right for all office workers | Flexibility vs organisational control |

---

## Prerequisites

- Python 3.11+
- An Azure AI Foundry project with a **gpt-4.1** (or gpt-4o) model deployment
- Azure CLI logged in (`az login`)

---

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate      # Windows
# source venv/bin/activate        # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env — fill in PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME
```

---

## Running

```bash
python agent.py
```

Each debate creates 4 agents in Foundry, runs the debate, and deletes all 4
agents on exit. A fresh set is created for each session.

---

## Key concepts illustrated

### ConnectedAgentTool — agent as a tool
A sub-agent is registered as a tool using `ConnectedAgentTool(id=agent.id, ...)`.
The conductor sees it as a callable tool, not as a peer. It passes a string input
and receives a string output — the sub-agent's full response.

### Hierarchical control
The conductor controls sequencing. It decides when to call each specialist and
in what order. The proponent and opponent never see each other's arguments directly
(the judge receives both, passed by the conductor).

### One thread, multiple agent hops
A single `threads.create()` call produces one thread. The conductor's run touches
three sub-agents internally, but from the user's perspective it's one call that
returns one response on one thread.

### Adversarial use of cooperative infrastructure
`ConnectedAgentTool` is designed for cooperative delegation. Using it for structured
opposition (proponent vs opponent) shows that the pattern is neutral — the
adversarial behaviour comes entirely from the prompts, not the SDK.

---

## File structure

```
04-policy-debate-simulator/
├── agent.py
├── prompts/
│   ├── conductor_prompt.txt    # Orchestration instructions
│   ├── proponent_prompt.txt    # Argue FOR the policy
│   ├── opponent_prompt.txt     # Argue AGAINST the policy
│   └── judge_prompt.txt        # Score and verdict rubric
├── requirements.txt
├── .env.example
├── .env
└── README.md
```
