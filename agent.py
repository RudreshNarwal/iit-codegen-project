"""Two-agent coding loop: the coder writes Python, the executor runs it, repeat until solved."""

import os
import sys
import tempfile
from types import SimpleNamespace

from autogen import AssistantAgent, UserProxyAgent
from autogen.code_utils import extract_code
from autogen.coding import LocalCommandLineCodeExecutor

OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"

SYSTEM_MESSAGE = """You are a Python coding agent. Solve the user's task by writing code.

- Reply with one complete, self-contained script in a single ```python block. It is executed
  automatically and you are shown its output.
- Print the results. Never call input(). Only Python runs: shell commands and pip install do not.
- The standard library, numpy and pandas are available.
- If execution fails, read the error and send the full corrected script.
- Once the output shows the task is solved, explain the result briefly WITHOUT a code block
  and end your message with TERMINATE."""


def is_done(message) -> bool:
    content = message.get("content") or ""
    # A reply holding both code and TERMINATE is not done: the code has not run yet.
    return content.rstrip().endswith("TERMINATE") and "```" not in content


def last_code(history) -> str:
    """Last Python block the coder wrote."""
    for message in reversed(history):
        if message.get("name") == "coder":
            blocks = [code for lang, code in extract_code(message.get("content") or "") if lang in ("python", "py")]
            if blocks:
                return blocks[-1]
    return ""


def last_output(history) -> str:
    """Last execution result reported by the executor."""
    for message in reversed(history):
        content = message.get("content") or ""
        if message.get("name") == "executor" and content.startswith("exitcode:"):
            return content
    return ""


def make_executor(work_dir, timeout):
    # ponytail: host process with a timeout, not a sandbox. Swap in
    # DockerCommandLineCodeExecutor when this runs on a server that has Docker.
    return LocalCommandLineCodeExecutor(
        timeout=timeout,
        work_dir=work_dir,
        # run generated code with this app's interpreter, whatever "python" is on PATH
        virtual_env_context=SimpleNamespace(bin_path=os.path.dirname(sys.executable)),
        execution_policies={"bash": False, "shell": False, "sh": False, "pwsh": False},
    )


def run_task(task, api_key, model=DEFAULT_MODEL, on_message=None, timeout=30, max_fixes=4):
    """Run the write/execute/fix loop and return the chat history.

    on_message(sender_name, text) is called for every message as it is sent.
    """
    with tempfile.TemporaryDirectory() as work_dir:  # private per run, deleted afterwards
        coder = AssistantAgent(
            "coder",
            system_message=SYSTEM_MESSAGE,
            llm_config={
                "config_list": [{"api_type": "openai", "model": model, "api_key": api_key, "base_url": OPENROUTER_URL}],
                "cache_seed": None,  # no on-disk response cache shared between visitors
            },
        )
        executor = UserProxyAgent(
            "executor",
            human_input_mode="NEVER",
            llm_config=False,
            max_consecutive_auto_reply=max_fixes + 1,
            is_termination_msg=is_done,
            code_execution_config={"executor": make_executor(work_dir, timeout)},
        )

        def report(sender, message, recipient, silent):
            if on_message:
                on_message(sender.name, message if isinstance(message, str) else message.get("content") or "")
            return message

        coder.register_hook("process_message_before_send", report)
        executor.register_hook("process_message_before_send", report)

        return executor.initiate_chat(coder, message=task, silent=True).chat_history
