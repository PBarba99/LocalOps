# Development plan

Completed checkpoints are marked below.

- [x] Agree on the package layout and dependencies.
- [x] Load and validate environment configuration.
- [x] Implement the restricted SSH client and command allowlist.
- [ ] Implement and test the three read-only tools.
- [ ] Integrate Ollama tool calling.
- [ ] Build the agent loop and structured tool-call logs.
- [ ] Add a small interactive command-line interface.
- [ ] Run a real end-to-end agent test against the home server.

The restricted SSH path has also passed a live smoke test using the approved
`HOSTNAME` command. This verifies SSH command execution, but is not yet the full
agent end-to-end test in the final checkpoint.
