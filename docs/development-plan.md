# Development plan

Completed checkpoints are marked below.

- [x] Agree on the package layout and dependencies.
- [x] Load and validate environment configuration.
- [x] Implement the restricted SSH client and command allowlist.
- [x] Implement and test the three read-only tools.
- [x] Integrate Ollama tool calling.
- [x] Build the agent loop and structured tool-call logs.
- [x] Add a small interactive command-line interface.
- [x] Run a real end-to-end agent test against the home server.

The restricted SSH path, all three inspection tools, and the complete
question-to-answer agent flow have passed live smoke tests. The interactive CLI
has also been verified against the live server with system, memory, and disk
questions, along with repeated attempts to request prohibited write operations.
