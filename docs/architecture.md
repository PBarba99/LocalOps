# Architecture notes

## Trust boundary

The model may select a named tool but must never construct or submit shell text.
Each tool maps to a reviewed command identifier inside the SSH layer, which will
own the fixed command allowlist.

## Planned flow

```text
User -> Agent -> Ollama -> named tool -> registry
     -> predefined tool -> approved SSH command -> Linux server
     -> command result -> Ollama -> final answer
```

## Version 0.1 non-goals

- Changing server state
- Arbitrary commands
- Service restarts
- Autonomous monitoring
- A graphical interface
- A large agent framework

