# Development plan

Completed checkpoints are marked below.

- [x] Agree on the package layout and dependencies.
- [x] Load and validate environment configuration.
- [x] Implement the restricted SSH client and command allowlist.
- [x] Implement and test the three read-only tools.
- [x] Integrate Ollama tool calling.
- [x] Build the agent loop and structured tool-call logs.
- [ ] Add a small interactive command-line interface.
- [ ] Run a real end-to-end agent test against the home server.

The restricted SSH path, all three inspection tools, and the complete
question-to-answer agent flow have passed live smoke tests. The final
end-to-end checkpoint remains open until the interactive CLI is included.
