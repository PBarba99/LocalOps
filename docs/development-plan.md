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

## Version 0.2

- [x] Define an immutable application response for unsupported requests.
- [x] Expose `decline_unsupported_request` as a strict zero-argument action.
- [x] Return the fixed response without SSH or a second model request.
- [x] Test valid inspection questions, unsupported general questions, and
  prohibited server modifications in the live CLI.

## Version 0.3 progress

- [x] Add fixed CPU-count and load-average commands to the immutable allowlist.
- [x] Implement and validate the `get_cpu_load` inspection tool.
- [x] Verify CPU-load selection and existing questions in the live CLI.
- [x] Add running and failed systemd service inspection.
- [x] Verify service selection, empty failed-service output, and existing tools
  in the live CLI.
- [x] Preload the configured Ollama model before displaying the first CLI
  prompt, with an honest loading indicator and clear startup failures.
- [x] Keep the model resident while the CLI session is active and test warm-up,
  readiness, and failure behavior.
- [x] Add restricted network interface and default-route status inspection.
- [x] Validate and execute bounded multi-tool requests sequentially.
- [x] Remove tool schemas from final-answer requests and require concrete
  synthesis from every returned result.
- [x] Use deterministic sampling for tool selection and validate multi-tool
  routing against the live server.
- [x] Add restricted available-package-update inspection using cached APT
  metadata, with the last recorded periodic refresh and missing-stamp handling.
- [x] Verify package-update selection and combined update/disk questions in the
  live CLI without refreshing metadata or installing packages.
- [ ] Add restricted sensor-temperature inspection after confirming server
  command support.
