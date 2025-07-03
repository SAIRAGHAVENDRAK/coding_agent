import os, textwrap, re
import streamlit as st
from dotenv import load_dotenv
from autogen import (
    AssistantAgent,
    UserProxyAgent,
    GroupChat,
    GroupChatManager,
)

# ─────────────────────────────────────────────────────────────
# 🔐  Load OpenAI key
# ─────────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY not found in env variables or .env")
    st.stop()

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")
if not DEFAULT_MODEL:
    st.error("❌ DEFAULT_MODEL not found in env variables or .env")
    st.stop()

# ─────────────────────────────────────────────────────────────
# 🏗️  Build full AutoGen ecosystem
#     (returns user_proxy, manager, group_chat)
# ─────────────────────────────────────────────────────────────
def build_autogen_system(model_name: str = DEFAULT_MODEL):
    cfg = [{"model": model_name, "api_key": OPENAI_API_KEY}]

    def make_agent(name, sys_msg, temp=0.0):
        return AssistantAgent(
            name=name,
            system_message=textwrap.dedent(sys_msg).strip(),
            llm_config={"config_list": cfg, "temperature": temp},
        )

    requirement_agent = make_agent(
        "RequirementAgent",
        """
        You are a software business analyst. Turn the user's natural‑language
        request into a clear, numbered requirement list. When finished call
        @CodingAgent and stay silent unless @‑mentioned.
        """,
    )

    coding_agent = make_agent(
        "CodingAgent",
        """
        You are an expert Python developer. Implement the requirements.
        Make sure to include inline comments and docstrings and error handling.
        Call @ReviewAgent ONLY when code has changed since the last review.
        After receiving REVIEW_ACCEPTED call @DocumentationAgent and never
        call @ReviewAgent again in this build.
        """,
        temp=0.2,
    )

    review_agent = make_agent(
        "ReviewAgent",
        """
        Review code from @CodingAgent.
        – If fixes are needed, address @CodingAgent with instructions.
        – If code is good, reply exactly REVIEW_ACCEPTED and call
          @DocumentationAgent. After that stay silent for this build.
        """,
    )

    documentation_agent = make_agent(
        "DocumentationAgent",
        """
        Write markdown documentation and full docstrings with headers and bullet points. Never call @ReviewAgent. 
        When finished call @TestCaseAgent.
        """,
    )

    test_agent = make_agent(
        "TestCaseAgent",
        """
        Produce pytest cases for the code. Never
        call @ReviewAgent. When finished call @DeployAgent.
        """,
        temp=0.2,
    )

    deploy_agent = make_agent(
        "DeployAgent",
        """
        Create requirements.txt, Dockerfile and run.sh. Never call
        @ReviewAgent. Then call @StreamlitUIAgent.
        """,
    )

    ui_agent = make_agent(
        "StreamlitUIAgent",
        """
        Build a Streamlit UI for the application. When you finish showing the
        complete UI code, end your message with PROJECT_COMPLETE on a
        separate line. Do not speak again after that token.
        """,
        temp=0.2,
    )

    # User proxy (no human input inside AutoGen loop)
    user_proxy = UserProxyAgent(
        name="User", human_input_mode="NEVER", code_execution_config=False
    )

    # GroupChat
    group_chat = GroupChat(
        agents=[
            user_proxy,
            requirement_agent,
            coding_agent,
            review_agent,
            documentation_agent,
            test_agent,
            deploy_agent,
            ui_agent,
        ],
        messages=[],
        max_round=8,
        speaker_selection_method="auto",
        allow_repeat_speaker=True,
    )

    # Termination checker for PROJECT_COMPLETE
    def is_termination_msg(msg: dict) -> bool:
        content = msg.get("content", "").upper()
        if isinstance(content, str) and "PROJECT_COMPLETE" in content:
            print("🚀 Termination Condition met! Ending conversation.")
            return True
        return False

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config={"config_list": cfg},
        is_termination_msg=is_termination_msg,
    )

    return user_proxy, manager, group_chat


# ─────────────────────────────────────────────────────────────
# 🌐  Streamlit UI
# ─────────────────────────────────────────────────────────────
st.set_page_config("AutoGen Multi‑Agent Demo", "🤖", layout="wide")
st.title("🤖 AutoGen Multi‑Agent Demo")
st.markdown(
    "Enter a software task. Agents will collaborate and display each step "
    "right here. They stop when the final UI agent prints **PROJECT_COMPLETE**."
    " Streaming is not supported yet, so you will see all messages at once in the end."
)

# Session state boot‑strap
if "user_proxy" not in st.session_state:
    (
        st.session_state.user_proxy,
        st.session_state.manager,
        st.session_state.group_chat,
    ) = build_autogen_system()
    st.session_state.chat_history = []  # list of all messages shown

# --- chat input ---
user_prompt = st.chat_input("Describe the software you want...")

if user_prompt:
    # show user's message
    with st.chat_message("User"):
        st.markdown(user_prompt)

    # Record current length to display only new agent messages later
    previous_len = len(st.session_state.group_chat.messages)

    # Kick off a new build cycle (mention RequirementAgent so it starts)
    st.session_state.user_proxy.initiate_chat(
        st.session_state.manager,
        message=f"@RequirementAgent: {user_prompt.strip()}",
    )

    # Display new messages
    new_msgs = st.session_state.group_chat.messages[previous_len:]
    for msg in new_msgs:
        if not isinstance(msg.get("content"), str):
            continue  # skip non‑string (e.g., code execution meta)
        with st.chat_message(msg["name"]):
            st.markdown(msg["content"])

# --- sidebar controls ---
with st.sidebar:
    st.subheader("Session")
    if st.button("🔄  Clear conversation"):
        for k in ("user_proxy", "manager", "group_chat", "chat_history"):
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown("Model: **{}**".format(DEFAULT_MODEL))
    st.markdown("Max rounds per build: **20**")
    st.markdown("---")
    st.markdown(
        "Pipeline order: Requirement → Coding → Review → Docs → Tests → Deploy → UI\n\n"
        "Conversation stops automatically when **PROJECT_COMPLETE** is seen."
    )
