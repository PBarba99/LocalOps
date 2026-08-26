# Development plan

Completed checkpoints are marked below.

- [x] Agree on the package layout and dependencies.
- [x] Load and validate environment configuration.
- [x] Implement the restricted SSH client and command allowlist.
- [x] Implement and test the three read-only tools.
- [ ] Integrate Ollama tool calling.
- [ ] Build the agent loop and structured tool-call logs.
- [ ] Add a small interactive command-line interface.
- [ ] Run a real end-to-end agent test against the home server.

The restricted SSH path and all three inspection tools have passed live smoke
tests. These verify real command execution, but are not yet the full agent
end-to-end test in the final checkpoint.
