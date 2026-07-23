---
name: chatgpt-collaboration
description: Coordinate Hermes Agent with an existing ordinary ChatGPT desktop conversation through /cg. Use when the user asks ChatGPT to review Hermes output, provide a second opinion, continue a project chat, or send guidance back into Hermes without Codex CLI or the OpenAI API.
version: 1.8.0
author: Local Hermes integration
license: MIT
platforms:
  - linux
  - windows
metadata:
  hermes:
    tags:
      - ChatGPT
      - Collaboration
      - Desktop-Automation
      - WSL
    related_skills: []
---

# ChatGPT Collaboration

Use this skill to coordinate Hermes with the ordinary ChatGPT desktop `Chat` surface. The bundled bridge uses Windows UI Automation; it does not use Codex CLI or the OpenAI API.

## Preconditions

- Hermes runs in WSL and the Windows ChatGPT desktop app is logged in.
- ChatGPT is in `ChatGPT > Chat`, not Work or Codex.
- The app was launched with `--force-renderer-accessibility`.
- A selected project or chat title must be visible in the ChatGPT sidebar.

## Command workflow

The installer adds a small CLI dispatcher because a Skill alone cannot intercept a slash command before the agent loop.

Continue the currently open ChatGPT conversation and place its reply in the Hermes composer as an editable draft:

```text
/cg
```

Add review instructions:

```text
/cg Review the latest Hermes result and give it one concrete next action
```

Select an existing conversation:

```text
/cg --chat "Chat title" Additional instruction
```

Select a project conversation:

```text
/cg --project "Project title" --chat "Chat title" Additional instruction
```

Use `-p` and `-c` as short forms. Put options before the additional instruction.

The default `/cg` stores the complete reply under `~/.hermes/pastes/` and prefills the composer with Hermes' native `[Pasted text #N: X lines → path]` reference. Add or edit instructions around that reference, then press Enter yourself. Hermes expands the referenced file through its existing paste-reference handler before starting the turn.

To skip editing and submit the reply automatically:

```text
/cg --run Additional instruction
```

To inspect ChatGPT's reply without filling or submitting the composer:

```text
/cg --show Additional instruction
```

Stop stale bridge processes and release their Windows mutex from Hermes:

```text
/cg --reset
```

`/cg --fuckyou` is an exact alias requested by the integration owner. If a running command still blocks the Hermes prompt, press `Ctrl+C` first, then run the reset command.

Forbid all foreground keyboard fallback:

```text
/cg --no-focus Additional instruction
```

This strict mode fails safely if the current ChatGPT accessibility tree has no writable background pattern.

Show command help:

```text
/cg --help
```

Typing `/c` in the Hermes composer should offer `/cg` from the central command registry. After installation or update, fully restart Hermes so the registry and completer are rebuilt.

## Behavioral rules

1. Use a compact delta protocol: send only `Hermes:` plus the latest non-empty assistant response and an optional `Requirement:` block.
2. Continue an existing ChatGPT conversation; never create a new conversation automatically.
3. Match project and chat titles exactly to prevent sending content to the wrong conversation.
4. Copy the complete assistant response through the response's native Copy control.
5. In default mode, save the complete response in `~/.hermes/pastes/`, prefill only a native Hermes paste reference, and wait for the user to edit and press Enter.
6. Only `--run` may submit the copied response automatically through the normal next-turn user-message path.
7. In `--show` mode, display the response without changing the composer or starting a Hermes turn.
8. Never extract browser cookies, access tokens, or private ChatGPT endpoints.
9. Fail when more than one visible project or chat has the requested exact title; never guess a destination.
10. Store generated paste files with user-only permissions (`0600`) in a user-only directory (`0700`).
11. Verify composer content before submission and verify that submission clears the composer before polling for a response.
12. Prefer UI Automation `ValuePattern` for input; use clipboard/keyboard input only as a focus-verified fallback.
13. Wait for generation completion or a response-structure change, let the action row settle, then invoke exactly one bottom response Copy control for the entire `/cg` run.
14. Allow only one bridge instance at a time through a Windows named mutex.
15. Treat a localized composer placeholder plus Chromium-added surrounding whitespace as empty, while preserving and rejecting every real non-empty draft.
16. During composer payload verification, ignore only terminal line feeds added by Chromium TextPattern; require every other character to match exactly.
17. Compare composer payloads with CR/LF removed because Chromium TextPattern may collapse Markdown paragraph breaks; require every non-line-break character to match exactly.
18. Let `--reset` bypass the bridge mutex and stop only same-session PowerShell processes whose command line launches `chatgpt_bridge.ps1` with `-File`.
19. Prefer background `ValuePattern` or `LegacyIAccessiblePattern` input. In normal mode, restore the original foreground window immediately after verified submission; in `--no-focus` mode, never use foreground keyboard input.

The default transfer prompt intentionally stays minimal. Do not add role explanations, workflow descriptions, repeated context, or formatting requirements. The existing ChatGPT conversation is responsible for retaining project context.

## Troubleshooting

- `Cannot find the Chat composer`: switch to `ChatGPT > Chat` and relaunch with accessibility enabled.
- `Cannot find project/chat`: expand the sidebar and make the exact title visible.
- No new Copy button: wait for generation to finish and ensure Windows is unlocked.
- Multiple historical responses are copied and nothing returns to Hermes: install version 1.7.0 or later; it removes the pre-send and double-copy probes and invokes Copy exactly once after completion.
- `Another /cg bridge is already running`: run `/cg --reset` or `/cg --fuckyou`; press `Ctrl+C` first if the current bridge still blocks the prompt.
- After `hermes update`: rerun the bundled installer because the small CLI dispatcher may be overwritten.
