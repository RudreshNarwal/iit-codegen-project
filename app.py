import streamlit as st

from agent import DEFAULT_MODEL, is_done, last_code, last_output, run_task

EXAMPLES = {
    "Fibonacci": "Print the first 20 Fibonacci numbers.",
    "Primes": "Find all prime numbers below 100 and print how many there are.",
    "Bubble sort": "Implement bubble sort and show it sorting [64, 34, 25, 12, 22, 11, 90].",
    "Word count": "Count word frequencies in 'the quick brown fox jumps over the lazy dog the fox' and print the top 3.",
}
MAX_OUTPUT_CHARS = 10_000


def clean(text):
    return text.replace("TERMINATE", "").strip()


def show_step(name, text):
    """Render one message inside the live status box as the agents exchange it."""
    if name == "coder":
        st.markdown("**Coder**")
        st.markdown(clean(text) or "_(empty reply)_")
    elif text.startswith("exitcode: 0"):
        st.success("Executor ran the code")
        st.code(text[:MAX_OUTPUT_CHARS], language=None)
    elif text.startswith("exitcode:"):
        st.error("Executor hit an error and sent it back to the coder")
        st.code(text[:MAX_OUTPUT_CHARS], language=None)


st.set_page_config(page_title="AutoGen Coding Agent", page_icon="🤖")
st.title("AutoGen Coding Agent")
st.caption("Describe a task. One agent writes Python, a second runs it, and they loop until it works.")

with st.sidebar:
    api_key = st.text_input(
        "OpenRouter API key", type="password", help="Get one at openrouter.ai/keys. Used for this run only, never stored."
    )
    model = st.text_input("Model", DEFAULT_MODEL, help="Any OpenRouter model ID.")
    timeout = st.slider("Execution timeout (seconds)", 10, 60, 30)
    st.caption(
        "Generated code runs on this server in a throwaway folder with the timeout above. "
        "It is not sandboxed, so only Python runs and shell commands are blocked."
    )

for column, (label, prompt) in zip(st.columns(len(EXAMPLES)), EXAMPLES.items()):
    column.button(label, width="stretch", on_click=lambda p=prompt: st.session_state.update(task=p))

task = st.text_area("Task", key="task", height=110, placeholder="e.g. Print the first 20 Fibonacci numbers.")

if st.button("Run", type="primary"):
    st.session_state.pop("history", None)
    if not api_key:
        st.warning("Enter your OpenRouter API key in the sidebar first.")
    elif not task.strip():
        st.warning("Describe a task first.")
    else:
        failure = None
        with st.status("Agents are working...", expanded=True) as status:
            try:
                st.session_state.history = run_task(task.strip(), api_key, model.strip(), show_step, timeout)
                status.update(label="Finished", state="complete", expanded=False)
            except Exception as error:  # bad key, unknown model, network: show the provider's message
                status.update(label="Run failed", state="error", expanded=False)
                failure = f"{type(error).__name__}: {error}"
        if failure:  # outside the status box, which collapses and would hide it
            st.error(failure)

# Kept in session_state so the result survives the rerun a download click triggers.
if history := st.session_state.get("history"):
    if is_done(history[-1]):
        st.success(clean(history[-1]["content"]))
    else:
        st.warning("The agents ran out of fix attempts before finishing. The last attempt is below.")

    code_tab, output_tab, conversation_tab = st.tabs(["Code", "Output", "Conversation"])
    with code_tab:
        if code := last_code(history):
            st.code(code, language="python")
            st.download_button("Download solution.py", code + "\n", "solution.py", "text/x-python")
        else:
            st.info("No code was written for this task.")
    with output_tab:
        st.code(last_output(history)[:MAX_OUTPUT_CHARS] or "Nothing was executed.", language=None)
    with conversation_tab:
        for message in history:
            with st.chat_message(message["name"], avatar="🧑‍💻" if message["name"] == "coder" else "⚙️"):
                st.markdown(clean(message["content"] or ""))
