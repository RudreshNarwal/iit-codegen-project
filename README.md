# AutoGen Coding Agent

A Streamlit app where two AutoGen agents solve a coding task together: one writes Python, the other runs it, and they loop until the code works.

Built by Rudresh Narwal.

## How it works

```
task ──> coder (AssistantAgent, LLM via OpenRouter)
            │  writes a Python script
            ▼
         executor (UserProxyAgent, no LLM)
            │  runs it, returns stdout or the traceback
            ▼
         coder reads the result: fixes the code, or explains the answer and ends with TERMINATE
```

- The loop stops when the coder replies with `TERMINATE` and no code, or after 5 executions.
- Each step appears on the page as it happens, not after the whole chat ends.
- The result is shown in three tabs: the final code (with a download button), its output, and the full conversation.

## Run it locally

Needs Python 3.10 or newer and an [OpenRouter API key](https://openrouter.ai/keys).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Paste the key into the sidebar, pick an example or type a task, and press Run. The key is used for that run only and is never written to disk.

## Tests

```bash
pip install pytest
pytest -q
```

The tests need no API key. They cover the termination check, the full write/run/fix loop with a scripted coder, the execution timeout, and the block on shell commands.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub.
2. At [share.streamlit.io](https://share.streamlit.io), choose New app, select the repo, branch `main`, main file `app.py`, and Python 3.13 under Advanced settings.
3. Do not add an API key under Secrets. Every visitor supplies their own, so a shared key would only bill you for their runs.

## Safety limits

Generated code runs on the machine hosting the app. It is not sandboxed. What limits it:

- Each run gets its own temporary folder, deleted when the run ends.
- Each script is killed after the timeout set in the sidebar (default 30 seconds).
- Only Python blocks are executed. Shell and PowerShell blocks are saved but never run.
- LLM responses are not cached to disk, so nothing is shared between visitors.

None of this stops a determined visitor from running harmful Python. On a server with Docker, replace `LocalCommandLineCodeExecutor` in `agent.py` with `DockerCommandLineCodeExecutor`. Streamlit Community Cloud does not offer Docker.

## Files

| File | Purpose |
|---|---|
| `agent.py` | The two agents, the executor, and the loop |
| `app.py` | The Streamlit page |
| `test_agent.py` | Tests |
| `requirements.txt` | `autogen[openai]==0.14.1`, `streamlit==1.65.0` |
