# 🤖 AutoGen Multi‑Agent Framework Demo

A self‑contained repository that showcases a **multi‑agent software‑generation pipeline** powered by **Microsoft AutoGen** and **OpenAI GPT‑4o**.  
The system takes a short natural‑language requirement and automatically delivers:

- structured requirements
- production‑quality Python code
- code review & feedback loop
- markdown documentation
- unit / integration tests
- deployment artifacts (Dockerfile, requirements.txt, run.sh)
- a working **Streamlit** front‑end

The conversation halts as soon as the UI agent prints **`PROJECT_COMPLETE`**.

---

## 📂 Folder Structure

your_project/
├── multi_agent_workflow.py # all agents + Streamlit UI in one file
├── tests/
│ └── test_pipeline.py # pytest suite covering 7 evaluation criteria
├── .env # holds OPENAI_API_KEY (git‑ignored)
├── requirements.txt # python dependencies
├── .gitignore # ignores .env, pycache, etc.
└── README.md # (this file)

---

## 🧠 Implemented Agents

| Stage | Agent                  | Purpose                                               |
| ----- | ---------------------- | ----------------------------------------------------- |
| 1️⃣    | **RequirementAgent**   | Turns NL request → numbered requirements              |
| 2️⃣    | **CodingAgent**        | Writes modular Python code                            |
| 3️⃣    | **ReviewAgent**        | Reviews code, issues fixes, finally `REVIEW_ACCEPTED` |
| 4️⃣    | **DocumentationAgent** | Generates markdown docs & docstrings                  |
| 5️⃣    | **TestCaseAgent**      | Produces pytest/unittest cases                        |
| 6️⃣    | **DeployAgent**        | Outputs `requirements.txt`, `Dockerfile`, `run.sh`    |
| 7️⃣    | **StreamlitUIAgent**   | Builds Streamlit UI → ends with `PROJECT_COMPLETE`    |
| 👤    | **UserProxyAgent**     | System driver (no human input during loop)            |

Agents hand‑off by @‑mentioning the next stage.  
`GroupChatManager` is configured with **`is_termination_msg`** so the chat stops the instant `PROJECT_COMPLETE` appears.

---

## 🏗️ Workflow & Architecture

User Prompt → RequirementAgent
↓
CodingAgent ↔ ReviewAgent (feedback loop until REVIEW_ACCEPTED)
↓
DocumentationAgent
↓
TestCaseAgent
↓
DeployAgent
↓
StreamlitUIAgent ──▶ PROJECT_COMPLETE

- **Speaker selection = `auto`** (agents dynamically decide who talks).
- **Safety cap** `max_round=20` to avoid infinite chatter.
- **Streamlit** chat interface displays every agent message live.

---

## ⚙️ Setup

```bash
# Make sure Python 3.10+ is installed.

# 1. Change directory to your root folder
cd root_folder/

# 2. Install deps
pip install -r requirements.txt

# 3. Add your OpenAI key
echo "OPENAI_API_KEY=sk-xxxxxxxx" > .env
```

## 🚀 Running the System

### Interactive Streamlit UI

```bash
streamlit run multi_agent_workflow.py
```

1. Browser opens at localhost:8501.
2. Enter a task (example prompts are below):
   - Build a Flask API that returns JSON {'greet':'hello'} at /hello.
   - Create an Python app that takes in a block of text and summarize it using transformers library.
3. Watch agents collaborate. Build ends when **PROJECT_COMPLETE** prints.

### Automated Tests

```bash
pytest -q
```

The suite checks:

- pipeline completes (PROJECT_COMPLETE, REVIEW_ACCEPTED)
- correct agent order & modularity
- code quality heuristics, error‑handling presence
- docs headings + usage example
- tests contain assert statements
- UI code includes streamlit (st.) references
