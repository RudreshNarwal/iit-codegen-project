from autogen import ConversableAgent
from autogen.coding import CodeBlock

from agent import is_done, last_code, last_output, make_executor, run_task

HISTORY = [
    {"name": "executor", "content": "Print the sum of 1..10"},
    {"name": "coder", "content": "```python\nprint(sum(range(10)))\n```"},
    {"name": "executor", "content": "exitcode: 0 (execution succeeded)\nCode output: 45\n"},
    {"name": "coder", "content": "Off by one, fixing.\n```python\nprint(sum(range(1, 11)))\n```"},
    {"name": "executor", "content": "exitcode: 0 (execution succeeded)\nCode output: 55\n"},
    {"name": "coder", "content": "The sum is 55. TERMINATE"},
]


def test_is_done():
    assert is_done({"content": "The sum is 55. TERMINATE"})
    assert is_done({"content": "Done.\nTERMINATE\n"})
    # code + TERMINATE in one reply must still get executed
    assert not is_done({"content": "```python\nprint(1)\n```\nTERMINATE"})
    assert not is_done({"content": "still working"})
    assert not is_done({"content": None})


def test_last_code_and_output():
    assert last_code(HISTORY) == "print(sum(range(1, 11)))"
    assert last_output(HISTORY).endswith("Code output: 55\n")
    assert last_code([]) == ""
    assert last_output(HISTORY[:1]) == ""


def test_run_task_fixes_failing_code(monkeypatch):
    """Whole loop with a scripted coder: broken code, then a fix, then TERMINATE."""
    replies = iter(["```python\nprint(1 / 0)\n```", "```python\nprint('fixed')\n```", "It prints fixed. TERMINATE"])
    monkeypatch.setattr(ConversableAgent, "generate_oai_reply", lambda self, *a, **k: (True, next(replies)))
    seen = []

    history = run_task("demo", api_key="unused", on_message=lambda name, text: seen.append(name), timeout=10)

    assert seen == ["executor", "coder", "executor", "coder", "executor", "coder"]
    assert "ZeroDivisionError" in history[2]["content"]
    assert last_code(history) == "print('fixed')"
    assert "exitcode: 0" in last_output(history) and "fixed" in last_output(history)
    assert is_done(history[-1])


def test_executor_runs_python(tmp_path):
    result = make_executor(tmp_path, timeout=10).execute_code_blocks([CodeBlock(code="print(6 * 7)", language="python")])
    assert result.exit_code == 0
    assert "42" in result.output


def test_executor_kills_infinite_loop(tmp_path):
    result = make_executor(tmp_path, timeout=2).execute_code_blocks(
        [CodeBlock(code="while True:\n    pass", language="python")]
    )
    assert result.exit_code != 0


def test_executor_does_not_run_shell(tmp_path):
    make_executor(tmp_path, timeout=10).execute_code_blocks([CodeBlock(code="touch pwned", language="sh")])
    assert not (tmp_path / "pwned").exists()
