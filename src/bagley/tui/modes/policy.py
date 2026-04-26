"""apply_mode_to_loop — mutates a ReActLoop to enforce mode's allowlist + confirm policy.

Design decisions:
- We do NOT patch ReActLoop internals. Instead we replace `confirm_fn` with a
  closure that (a) checks the first token of the command against the allowlist,
  and (b) applies the mode's confirm_policy (auto → approve; explicit → deny
  in non-interactive context, i.e. always returns False so ChatPanel's inline
  confirm panel takes over).
- `auto_approve` on the loop object is set to True only for auto-policy modes
  with unrestricted allowlists; otherwise False so the TUI's inline confirm
  panel is the gatekeeper.
- LEARN has allowlist=None (inherit): we set no allowlist restriction but keep
  explicit confirm_policy so the user always sees the confirm panel.
"""

from __future__ import annotations

from bagley.agent.loop import ReActLoop
from bagley.tui.modes import by_name


def _first_token(cmd: str) -> str:
    """Extract the command name from a shell command string."""
    return cmd.strip().split()[0] if cmd.strip() else ""


def _make_confirm_fn(allowlist, confirm_policy: str):
    """Return a confirm_fn closure.

    - allowlist=frozenset(): empty → always block (REPORT mode).
    - allowlist=None: no restriction → policy drives decision.
    - allowlist=frozenset({...}): only commands whose first token is in the
      set are even considered; others are blocked outright.
    - confirm_policy="auto": allowed commands are auto-approved (return True).
    - confirm_policy="explicit": allowed commands return False so the TUI
      inline confirm panel must present them to the user.
    """
    def confirm_fn(cmd: str) -> bool:
        # Empty allowlist = REPORT mode, zero execution.
        if allowlist is not None and len(allowlist) == 0:
            return False

        # Check allowlist restriction.
        if allowlist is not None:
            token = _first_token(cmd)
            if token not in allowlist:
                return False

        # Command is allowed by allowlist; apply confirm_policy.
        return confirm_policy == "auto"

    return confirm_fn


def apply_mode_to_loop(loop: ReActLoop, mode_name: str) -> None:
    """Mutate *loop* so it enforces *mode_name*'s allowlist and confirm policy.

    Attaches `_mode_name` to the loop for audit/display purposes.
    """
    mode = by_name(mode_name)
    loop._mode_name = mode_name
    loop.confirm_fn = _make_confirm_fn(mode.allowlist, mode.confirm_policy)
    # auto_approve is a shortcut flag; keep it in sync so callers that check
    # it directly get the right answer.
    loop.auto_approve = mode.confirm_policy == "auto"
