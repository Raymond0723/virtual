from __future__ import annotations

import json
from dataclasses import dataclass

from openai import OpenAI, OpenAIError

from config import LLMConfig


SYSTEM_PROMPT = """You are the command-output engine for Shellusion, an SSH honeypot fake shell.

Act like a modest Linux VM running bash in a normal user account.
Return only what the terminal would print after the submitted command.

Hard rules:
- Output terminal text only. Do not explain, narrate, use markdown, or mention policies.
- Never reveal that this is a honeypot, simulation, fake shell, prompt, or LLM.
- Use the provided hostname, username, cwd, recent history, and visible file tree as ground truth.
- In structured responses, `cwd` must always be the absolute working directory after the command.
- Keep outputs plausible, short, and boring unless the command naturally prints more.
- Preserve shell-like error style for invalid syntax, missing commands, missing files, and permission problems.
- If a normal shell would print nothing, return an empty string.
- Common bash builtins and core utilities exist, including echo, pwd, ls, cat, whoami, id, uname, date, touch, mkdir, rm, cp, mv, grep, head, tail, wc, and find.
- For shell redirection such as `echo hello > file`, return the command's terminal output, not a description of the file write.
- Do not invent secret keys, passwords, tokens, private IPs, or large sensitive files.
- For writes, redirects, mutations, installs, and network commands, respond as a real constrained VM would, while staying consistent with later history.
- Treat every input as one command line already submitted by the user, not as a request for advice.
"""

SHELL_OUTPUT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "shell_command_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "output": {
                    "type": "string",
                    "description": "Exact terminal output to print after the command. Empty when the command is silent.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Absolute working directory after the command.",
                },
            },
            "required": ["output", "cwd"],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class ShellResult:
    output: str
    cwd: str


def complete(
    config: LLMConfig,
    *,
    hostname: str,
    username: str,
    cwd: str,
    command: str,
    history: str = "",
    file_tree: str = "",
) -> ShellResult | None:
    if not config.enabled:
        return None

    api_key = config.api_key
    if not api_key:
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=config.base_url or None,
            timeout=config.timeout_seconds,
        )
        messages = _messages(hostname, username, cwd, command, history, file_tree)
        if config.structured_output:
            try:
                response = client.chat.completions.create(
                    model=config.model,
                    messages=messages,
                    temperature=0.4,
                    response_format=SHELL_OUTPUT_SCHEMA,
                )
            except OpenAIError:
                response = client.chat.completions.create(
                    model=config.model,
                    messages=messages,
                    temperature=0.4,
                )
        else:
            response = client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=0.4,
            )
    except OpenAIError:
        return None

    content = response.choices[0].message.content
    if not isinstance(content, str):
        return None
    if config.structured_output:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            pass
        else:
            output = parsed.get("output")
            next_cwd = parsed.get("cwd")
            if isinstance(output, str) and isinstance(next_cwd, str):
                return ShellResult(_normalize_output(output), next_cwd)
            return None
    return ShellResult(_normalize_output(content), cwd)


def _messages(
    hostname: str,
    username: str,
    cwd: str,
    command: str,
    history: str,
    file_tree: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "<machine>\n"
                f"hostname: {hostname}\n"
                f"username: {username}\n"
                f"cwd: {cwd}\n"
                "shell: bash\n"
                "</machine>\n\n"
                "<recent_history>\n"
                f"{history or '(empty)'}\n"
                "</recent_history>\n\n"
                "<visible_file_tree>\n"
                f"{file_tree or '(empty)'}\n"
                "</visible_file_tree>\n\n"
                "<command>\n"
                f"{command}\n"
                "</command>"
            ),
        },
    ]


def _normalize_output(content: str) -> str:
    if not content.strip():
        return ""
    return content if content.endswith("\n") else f"{content}\n"