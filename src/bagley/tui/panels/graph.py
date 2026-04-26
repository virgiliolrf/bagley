"""GraphPane: full-screen F7 network graph widget.

Renders hosts as unicode box chars, edges as lines, and marks the
current target with a star. Uses ``graph_layout.layout_to_grid`` to project a
networkx Graph onto the terminal grid.

Textual 8.2.4: ``render()`` returns a ``Strip`` list via ``render_line()``
or we override ``render()`` to return a Rich ``Text`` object for the whole
widget. For simplicity this implementation uses a custom ``render_line()``
approach based on a pre-rendered grid buffer.

Operator interaction:
    - Click on a node label fires ``NodeClicked(node_id)`` message.
    - update_graph(G, current_target) rebuilds the buffer and triggers a refresh.
"""
from __future__ import annotations

from typing import Optional

import networkx as nx
from rich.segment import Segment
from rich.style import Style
from textual.message import Message
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

from bagley.tui.services.graph_layout import GridNode, EdgePath, layout_to_grid

_NODE_CHAR = "●"
_STAR_CHAR = "★"
_HORIZ = "─"
_VERT = "│"
_STYLE_NODE = Style(color="cyan", bold=True)
_STYLE_TARGET = Style(color="bright_yellow", bold=True)
_STYLE_EDGE = Style(color="bright_black")
_STYLE_LABEL = Style(color="white")


class GraphPane(Widget):
    """Unicode network graph. Toggle full-screen with F7 via BagleyApp binding."""

    class NodeClicked(Message):
        def __init__(self, node_id: str) -> None:
            super().__init__()
            self.node_id = node_id

    def __init__(
        self,
        graph: Optional[nx.Graph] = None,
        current_target: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._graph = graph if graph is not None else nx.Graph()
        self._current_target = current_target
        self._grid: list[list[str]] = []
        self._style_grid: list[list[Style]] = []

    def on_mount(self) -> None:
        self._rebuild()

    def update_graph(self, graph: nx.Graph, current_target: str = "") -> None:
        self._graph = graph
        self._current_target = current_target
        self._rebuild()
        self.refresh()

    def _rebuild(self) -> None:
        """Rasterise graph onto a character grid."""
        w = self.size.width or 80
        h = self.size.height or 24
        self._grid = [[" "] * w for _ in range(h)]
        self._style_grid = [[Style.null()] * w for _ in range(h)]
        if len(self._graph) == 0:
            return
        nodes, edges = layout_to_grid(self._graph, width=w, height=h)
        self._draw_edges(edges)
        self._draw_nodes(nodes)

    def _draw_edges(self, edges: list[EdgePath]) -> None:
        for e in edges:
            self._draw_line(e.src_col, e.src_row, e.dst_col, e.dst_row)

    def _draw_line(self, c0: int, r0: int, c1: int, r1: int) -> None:
        """Bresenham line drawing onto the char grid."""
        dc = abs(c1 - c0)
        dr = abs(r1 - r0)
        sc = 1 if c0 < c1 else -1
        sr = 1 if r0 < r1 else -1
        err = dc - dr
        c, r = c0, r0
        while True:
            h = self.size.height or 24
            w = self.size.width or 80
            if 0 <= r < h and 0 <= c < w:
                if dc > dr:
                    self._grid[r][c] = _HORIZ
                else:
                    self._grid[r][c] = _VERT
                self._style_grid[r][c] = _STYLE_EDGE
            if c == c1 and r == r1:
                break
            e2 = 2 * err
            if e2 > -dr:
                err -= dr
                c += sc
            if e2 < dc:
                err += dc
                r += sr

    def _draw_nodes(self, nodes: list[GridNode]) -> None:
        for n in nodes:
            r, c = n.row, n.col
            h = self.size.height or 24
            w = self.size.width or 80
            if not (0 <= r < h and 0 <= c < w):
                continue
            is_target = n.node_id == self._current_target
            char = _STAR_CHAR if is_target else _NODE_CHAR
            style = _STYLE_TARGET if is_target else _STYLE_NODE
            self._grid[r][c] = char
            self._style_grid[r][c] = style
            # Draw label to the right
            label = n.label[:12]  # truncate to avoid overflow
            for i, ch in enumerate(label):
                lc = c + 1 + i
                if 0 <= lc < w:
                    self._grid[r][lc] = ch
                    self._style_grid[r][lc] = _STYLE_LABEL

    def render_line(self, y: int) -> Strip:
        if y >= len(self._grid):
            return Strip.blank(self.size.width)
        row = self._grid[y]
        style_row = self._style_grid[y]
        segments: list[Segment] = []
        for ch, st in zip(row, style_row):
            segments.append(Segment(ch, st))
        return Strip(segments)

    def render_to_text(self) -> str:
        """Return all grid rows joined by newlines for testing."""
        return "\n".join("".join(row) for row in self._grid)

    def on_resize(self) -> None:
        self._rebuild()
        self.refresh()
