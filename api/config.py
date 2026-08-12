from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tomllib

from dotenv import load_dotenv


DEFAULT_DENY_COMMANDS = frozenset(
    {
        "vi",
        "vim",
        "nano",
        "emacs",
        "ed",
        "less",
        "more",
        "man",
        "info",
        "top",
        "htop",
        "watch",
        "tmux",
        "screen",
        "ssh",
        "sftp",
        "ftp",
        "telnet",
        "nc",
        "mysql",
        "psql",
        "sqlite3",
        "redis-cli",
    }
)


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool = False
    base_url: str = ""
    api_key_env: str = "LLM_API_KEY"
    model: str = "gpt-4o-mini"
    timeout_seconds: int = 20
    structured_output: bool = True

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env) or None


@dataclass(frozen=True)
class ShellConfig:
    hostname: str = "ismplab"
    username: str = "user"
    home: str = "/home/user"
    prompt: str = "{username}@{hostname}:{cwd}$ "
    scenario_root: Path = Path("scenario/default/home/user")
    log_path: Path = Path("logs/sessions.jsonl")
    deny: frozenset[str] = DEFAULT_DENY_COMMANDS
    llm: LLMConfig = LLMConfig()


def load_config(path: str | Path | None = None) -> ShellConfig:
    load_dotenv()

    config_path = Path(path or "config.toml")
    if not config_path.exists():
        config_path = Path("config.example.toml")
    if not config_path.exists():
        return ShellConfig()

    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    shell = raw.get("shell", {})
    llm = raw.get("llm", {})
    return ShellConfig(
        hostname=str(shell.get("hostname", "ismplab")),
        username=str(shell.get("username", "user")),
        home=str(shell.get("home", "/home/user")),
        prompt=str(shell.get("prompt", "{username}@{hostname}:{cwd}$ ")),
        scenario_root=Path(shell.get("scenario_root", "scenario/default/home/user")),
        log_path=Path(shell.get("log_path", "logs/sessions.jsonl")),
        deny=frozenset(str(command) for command in shell.get("deny", DEFAULT_DENY_COMMANDS)),
        llm=LLMConfig(
            enabled=bool(llm.get("enabled", False)),
            base_url=str(llm.get("base_url", "")),
            api_key_env=str(llm.get("api_key_env", "LLM_API_KEY")),
            model=str(llm.get("model", "gpt-4o-mini")),
            timeout_seconds=int(llm.get("timeout_seconds", 20)),
            structured_output=bool(llm.get("structured_output", True)),
        ),
    )