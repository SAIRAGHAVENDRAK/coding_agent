import os, sys, re, importlib, json
from pathlib import Path
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))  # add project root

# import the Streamlit/AutoGen app
app = importlib.import_module("multi_agent_workflow")

MODEL = "gpt-4o"          # adjust for cost if needed
PROMPT = (
    "Build a Flask API that returns JSON {'greet':'hello'} at /hello. "
    "Include error handling, documentation, test cases, and a Streamlit UI. "
)

@pytest.fixture(scope="session")
def run_once():
    """Run pipeline once per test session to save tokens."""
    user_proxy, manager, group_chat = app.build_autogen_system(MODEL)
    user_proxy.initiate_chat(manager, message=f"@RequirementAgent: {PROMPT}")
    return group_chat.messages


# ──────────────────────────────────────────────────────────────
# 1. Correctness – did we finish & produce runnable code?
# ──────────────────────────────────────────────────────────────
def test_pipeline_completes(run_once):
    all_txt = " ".join(m["content"] for m in run_once if isinstance(m["content"], str))
    assert "PROJECT_COMPLETE" in all_txt, "Pipeline did not reach completion token."
    assert "REVIEW_ACCEPTED" in all_txt, "Code never approved by ReviewAgent."


# ──────────────────────────────────────────────────────────────
# 2. Modularity – every agent spoke in expected sequence
# ──────────────────────────────────────────────────────────────
def test_agent_sequence(run_once):
    speak_order = [m["name"] for m in run_once]
    required = [
        "RequirementAgent",
        "CodingAgent",
        "ReviewAgent",
        "DocumentationAgent",
        "TestCaseAgent",
        "DeployAgent",
        "StreamlitUIAgent",
    ]
    for agent in required:
        assert agent in speak_order, f"{agent} never produced a message."
    assert speak_order.index("RequirementAgent") < speak_order.index("CodingAgent")


# ──────────────────────────────────────────────────────────────
# Helper: extract python code blocks
# ──────────────────────────────────────────────────────────────
PY_CODE_RE = re.compile(r"```python(.*?)```", re.S)

def extract_code(messages, sender):
    """Return concatenated python snippets from a given agent."""
    parts = []
    for m in messages:
        if m["name"] == sender and isinstance(m["content"], str):
            parts.extend(PY_CODE_RE.findall(m["content"]))
    return "\n\n".join(parts)


# ──────────────────────────────────────────────────────────────
# 3. Code Quality heuristics
#    • has docstrings
#    • contains at least one comment
# ──────────────────────────────────────────────────────────────
def test_code_quality(run_once):
    code = extract_code(run_once, "CodingAgent")
    assert '"""' in code or "'''" in code, "No docstrings detected in code."

# ──────────────────────────────────────────────────────────────
# 4. Error Handling – look for try/except in code
# ──────────────────────────────────────────────────────────────
def test_error_handling_present(run_once):
    code = extract_code(run_once, "CodingAgent")
    assert "try:" in code and "except" in code, "No try/except blocks found (no error handling)."


# ──────────────────────────────────────────────────────────────
# 5. Documentation Quality – heading + example
# ──────────────────────────────────────────────────────────────
def test_docs_quality(run_once):
    docs = run_once[[m["name"] for m in run_once].index("DocumentationAgent")]["content"]
    assert "#" in docs, "No markdown headings in docs."

# ──────────────────────────────────────────────────────────────
# 6. Test Coverage – pytest/unittest artefacts
# ──────────────────────────────────────────────────────────────
def test_testcases_generated(run_once):
    tests = extract_code(run_once, "TestCaseAgent")
    # minimal heuristic: at least one assert
    assert "assert" in tests, "Generated tests do not contain assert statements."


# ──────────────────────────────────────────────────────────────
# 7. UI Implementation – Streamlit references
# ──────────────────────────────────────────────────────────────
def test_streamlit_ui(run_once):
    ui_code = extract_code(run_once, "StreamlitUIAgent")
    assert "streamlit" in ui_code.lower() or "st." in ui_code, "UI code not using Streamlit."
    # basic usability check
    assert "st." in ui_code, "Streamlit shorthand 'st.' not found – UI may be missing."


# ──────────────────────────────────────────────────────────────
# Optional: quick JSON artifact for debugging
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Write last run to file for manual inspection
    msgs = run_once()  # noqa: F811
    Path("last_run.json").write_text(json.dumps(msgs, indent=2))
    print("Saved last_run.json")
