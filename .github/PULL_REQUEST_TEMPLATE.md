## Summary

Describe the problem and the smallest relevant change.

## Validation

- [ ] Python files compile.
- [ ] `chatgpt_bridge.ps1` remains ASCII-only and passes Windows PowerShell parsing.
- [ ] Isolated install and uninstall pass.
- [ ] `/cg` sends once and invokes one response-level Copy.
- [ ] Draft protection, mutex behavior, and foreground restoration were checked.
- [ ] Documentation and changelog were updated when behavior changed.
- [ ] Logs, screenshots, paths, and fixtures are free of personal or secret data.

## Environment

- Windows:
- WSL:
- Hermes:
- ChatGPT desktop app:

## Security impact

State whether this changes clipboard handling, process termination, destination selection, input verification, or automatic submission.
