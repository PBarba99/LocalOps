# Changelog

All notable changes to LocalOps are documented in this file.

## [Unreleased]

### Added

- Added `get_cpu_load`, backed by fixed `nproc` and `/proc/loadavg` commands, to
  report CPU capacity and current 1-, 5-, and 15-minute load averages.

## [0.2.0] - 2026-09-03

### Added

- Added `decline_unsupported_request` as a strictly validated zero-argument
  control action.
- Added an immutable application-owned response for questions outside the
  available read-only inspection tools.
- Added tests covering control-action mutation, injection, invalid arguments,
  and orchestration behavior.
- Added GitHub Actions testing across Python 3.11 through 3.14, including
  dependency update pull requests.
- Added weekly grouped Dependabot version updates.
- Enabled Dependabot security and malware alerts, secret scanning, push
  protection, and CodeQL analysis for the public repository.

### Changed

- Unsupported questions and server modification requests now return the fixed
  local response without opening an SSH connection.
- The decline path no longer asks the model to compose or rewrite its answer.
- Expanded supported dependency ranges for Paramiko 5 and pytest 9 after CI,
  unit, and live SSH validation.

## [0.1.0] - 2026-09-01

### Added

- Added immutable configuration, a restricted SSH client, and six fixed
  read-only commands.
- Added system, memory, and disk inspection tools.
- Added local Ollama tool selection, corrective validation retry, grounded
  answers, structured metrics, and an interactive CLI.
- Added unit and integration tests for the initial application boundaries.

[Unreleased]: https://github.com/PBarba99/LocalOps/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/PBarba99/LocalOps/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/PBarba99/LocalOps/releases/tag/v0.1.0
