"""InspectorPane — bottom-right dockable pane for selection inspection.

Usage:
    pane = InspectorPane()
    pane.inspect("CVE-2021-44228")   # classifies, renders, shows pane
    # Esc closes it; X button also dismisses

Layout: hidden by default (display: none). inspect() sets display=True.
Position: docked bottom-right via CSS. Width 50, height auto up to 18.

The pane does NOT open as a modal — it overlays the dashboard layout.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

from bagley.tui.interactions.inspector_actions import InspectorAction, actions_for
from bagley.tui.interactions.selection import ClassifyResult, SelectionType, classify

# Color map for type badges
_TYPE_COLOR: dict[SelectionType, str] = {
    SelectionType.IPV4:    "cyan",
    SelectionType.CVE:     "red",
    SelectionType.MD5:     "yellow",
    SelectionType.SHA256:  "yellow",
    SelectionType.URL:     "blue",
    SelectionType.PORT:    "magenta",
    SelectionType.PATH:    "green",
    SelectionType.UNKNOWN: "dim",
}


class InspectorPane(Vertical):
    DEFAULT_CSS = """
    InspectorPane {
        dock: bottom;
        width: 52;
        height: auto;
        max-height: 20;
        border: round $warning;
        background: $panel;
        padding: 0 1;
        display: none;
        offset: 0 0;
        layer: overlay;
    }
    InspectorPane #inspector-type-label {
        height: 1;
        color: $text;
    }
    InspectorPane #inspector-value-label {
        height: 1;
        color: $text-muted;
        overflow: hidden hidden;
    }
    InspectorPane #inspector-actions {
        height: auto;
    }
    InspectorPane Button {
        height: 1;
        min-width: 20;
        margin: 0;
    }
    InspectorPane #inspector-close-btn {
        dock: top;
        width: 3;
        height: 1;
        background: $error;
        color: $text;
        border: none;
    }
    """

    _current_result: ClassifyResult | None = None

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.can_focus = True

    def on_mount(self) -> None:
        # Hidden by default — shown via inspect().
        self.visible = False
        self.display = False

    def compose(self) -> ComposeResult:
        yield Button("X", id="inspector-close-btn", variant="error")
        yield Label("", id="inspector-type-label")
        yield Label("", id="inspector-value-label")
        yield Vertical(id="inspector-actions")

    def inspect(self, text: str) -> None:
        """Classify *text*, populate pane content, and make the pane visible."""
        result = classify(text)
        self._current_result = result
        self._render_result(result)
        self.display = True
        self.visible = True
        self.focus()

    def _render_result(self, result: ClassifyResult) -> None:
        color = _TYPE_COLOR.get(result.type, "dim")
        type_label = self.query_one("#inspector-type-label", Label)
        type_label.update(f"[bold {color}]{result.type.name}[/]  Inspector")

        value_label = self.query_one("#inspector-value-label", Label)
        truncated = result.value[:42] + "…" if len(result.value) > 42 else result.value
        value_label.update(f"[dim]{truncated}[/]")

        actions_container = self.query_one("#inspector-actions", Vertical)
        actions_container.remove_children()
        for action in actions_for(result):
            btn = Button(action.label, id=f"action-{_safe_id(action.label)}")
            btn._inspector_action = action  # stash for dispatch
            actions_container.mount(btn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "inspector-close-btn":
            self.display = False
            self.visible = False
            event.stop()
            return
        action: InspectorAction | None = getattr(event.button, "_inspector_action", None)
        if action is None:
            return
        if action.is_tui_action:
            self.app.post_message(InspectorDispatch(action))
        else:
            # Non-TUI actions: send command string to chat panel as if user typed it.
            try:
                from bagley.tui.panels.chat import ChatPanel
                chat = self.app.query_one(ChatPanel)
                chat.submit_command(action.command)
            except Exception:
                pass
        self.display = False
        self.visible = False
        event.stop()

    def key_escape(self) -> None:
        self.display = False
        self.visible = False


def _safe_id(label: str) -> str:
    """Convert a label to a safe CSS id fragment."""
    return label.lower().replace(" ", "-").replace("(", "").replace(")", "")[:24]


class InspectorDispatch:
    """Message posted to the app when a TUI action is dispatched from the inspector."""

    def __init__(self, action: InspectorAction) -> None:
        self.action = action
