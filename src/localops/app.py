"""Command-line entry point."""

from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

import logging
import ollama
import paramiko

from .agent import ServerAssistant
from .config import Settings, load_settings
from .ollama_client import OllamaClient
from .ssh_client import SSHClient
from .tools.errors import ToolCommandError
from .tools.registry import InvalidToolRequest, ToolRegistry

DEFAULT_LOG_PATH = Path(".localops/localops.log")


def configure_logging(
    settings: Settings,
    log_path: Path = DEFAULT_LOG_PATH,
) -> Path:
    """Write LocalOps JSON events to a bounded, ignored local log file."""

    log_path.parent.mkdir(parents=True, exist_ok=True)
    localops_logger = logging.getLogger("localops")
    localops_logger.setLevel(settings.log_level)
    localops_logger.propagate = False

    for handler in tuple(localops_logger.handlers):
        if getattr(handler, "_localops_owned", False):
            localops_logger.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(settings.log_level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler._localops_owned = True  # type: ignore[attr-defined]
    localops_logger.addHandler(handler)
    return log_path


def build_assistant(settings: Settings | None = None) -> ServerAssistant:
    """Construct LocalOps from one validated configuration object."""

    settings = settings or load_settings()
    ssh = SSHClient(settings=settings)
    return ServerAssistant(
        model=OllamaClient(settings=settings),
        tools=ToolRegistry(ssh=ssh),
    )


def run_cli(
    assistant: ServerAssistant,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run the interactive LocalOps question-and-answer loop."""

    output_fn("LocalOps - read-only server assistant")
    output_fn("Type 'exit' or 'quit' to stop.")

    while True:
        try:
            question = input_fn("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("Goodbye.")
            return

        if question.lower() in {"exit", "quit"}:
            output_fn("Goodbye.")
            return
        if not question:
            output_fn("Please enter a question.")
            continue

        try:
            answer = assistant.answer(question)
        except InvalidToolRequest:
            output_fn(
                "Error: the local model could not produce a valid tool request "
                "after one correction. Try rephrasing the question."
            )
        except ToolCommandError as exc:
            diagnostic = (exc.result.stderr or exc.result.stdout).strip()
            detail = f" Details: {diagnostic}" if diagnostic else ""
            output_fn(
                f"Error: {exc.command_id.name} failed with exit code "
                f"{exc.result.exit_code}.{detail}"
            )
        except paramiko.AuthenticationException:
            output_fn("Error: SSH authentication failed. Check the configured key.")
        except paramiko.BadHostKeyException:
            output_fn("Error: the server SSH host key did not match known_hosts.")
        except TimeoutError:
            output_fn(
                "Error: the connection or command timed out. Check the VPN and "
                "server availability."
            )
        except (ollama.RequestError, ollama.ResponseError):
            output_fn(
                "Error: the local Ollama request failed. Check that Ollama and "
                "the configured model are available."
            )
        except (paramiko.SSHException, OSError):
            output_fn(
                "Error: a connection failed. Check Ollama, the VPN, and the "
                "server availability."
            )
        except KeyboardInterrupt:
            output_fn("Goodbye.")
            return
        else:
            output_fn(f"LocalOps: {answer}")


def main() -> None:
    settings = load_settings()
    configure_logging(settings)
    run_cli(build_assistant(settings))


if __name__ == "__main__":
    main()
