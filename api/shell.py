from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

import llm
from config import ShellConfig


@dataclass
class FakeShell:
    config: ShellConfig
    session_history: list[tuple[str, str]] = field(default_factory=list)
    cwd: PurePosixPath | None = None

    def prompt(self) -> str:
        return self.config.prompt.format(
            username=self.config.username,
            hostname=self.config.hostname,
            cwd=self._display_cwd(),
        )

    def run(self, line: str) -> tuple[str, bool]:
        command = line.strip()
        if not command:
            return "", True
        if command in {"exit", "logout", "quit"}:
            return self._finish(command, "logout\n", False)

        command_name = command.split(maxsplit=1)[0]
        if command_name in self.config.deny:
            return self._finish(command, f"{command_name}: permission denied\n", True)

        result = self._complete_with_context(command)
        if result is None:
            output = f"{command_name}: command not found\n"
        else:
            output = result.output
            next_cwd = PurePosixPath(result.cwd)
            if next_cwd.is_absolute():
                self.cwd = next_cwd
        return self._finish(command, output, True)

    def _complete_with_context(self, command: str) -> llm.ShellResult | None:
        return llm.complete(
            self.config.llm,
            hostname=self.config.hostname,
            username=self.config.username,
            cwd=str(self._cwd()),
            command=command,
            history=self._format_session_history(),
            file_tree=self._format_file_tree(),
        )

    def _finish(self, command: str, output: str, alive: bool) -> tuple[str, bool]:
        self.session_history.append((command, output))
        self.session_history = self.session_history[-20:]
        return output, alive

    def _format_session_history(self) -> str:
        lines = []
        for index, (command, output) in enumerate(self.session_history[-10:], start=1):
            clipped = output.strip()
            if len(clipped) > 800:
                clipped = clipped[:800] + "\n...[truncated]"
            lines.append(f"[{index}] $ {command}\n{clipped or '[no output]'}")
        return "\n\n".join(lines)

    def _cwd(self) -> PurePosixPath:
        if self.cwd is None:
            self.cwd = PurePosixPath(self.config.home)
        return self.cwd

    def _display_cwd(self) -> str:
        cwd = self._cwd()
        home = PurePosixPath(self.config.home)
        if cwd == home:
            return "~"
        if cwd.is_relative_to(home):
            return str(PurePosixPath("~") / cwd.relative_to(home))
        return str(cwd)

    def _format_file_tree(self) -> str:
        paths: set[str] = set()
        root = self.config.scenario_root
        if root.exists():
            for item in root.rglob("*"):
                if item.name.startswith("."):
                    continue
                rel = item.relative_to(root)
                posix_path = PurePosixPath(self.config.home) / PurePosixPath(*rel.parts)
                paths.add(str(PurePosixPath("/") / posix_path) + ("/" if item.is_dir() else ""))
        return "\n".join(sorted(paths)[:80])