"""Convert a networkx Graph into integer grid coordinates for unicode rendering.

``layout_to_grid`` is a pure function: same graph + same seed → same output.
It uses networkx's spring layout (Fruchterman-Reingold) and maps the resulting
[-1, 1] float space linearly onto the integer grid [0, width) × [0, height).
A 2-unit margin is applied so labels never touch the terminal edge.

Returns:
    nodes: list[GridNode]  — one per graph node
    edges: list[EdgePath]  — one per graph edge, with src/dst grid coords
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import networkx as nx


@dataclass
class GridNode:
    node_id: str
    col: int
    row: int
    label: str
    kind: str          # "host", "gateway", "pivot", etc.


@dataclass
class EdgePath:
    src_id: str
    dst_id: str
    src_col: int
    src_row: int
    dst_col: int
    dst_row: int
    relation: str      # "scanned", "routed-via", "pivoted", "shell-obtained"


def layout_to_grid(
    G: nx.Graph,
    width: int,
    height: int,
    seed: int = 0,
    margin: int = 2,
) -> tuple[list[GridNode], list[EdgePath]]:
    """Project networkx spring layout onto an integer terminal grid.

    Args:
        G:      networkx Graph with optional node attrs ``label`` and ``kind``
                and optional edge attr ``relation``.
        width:  terminal columns available (passed by GraphPane).
        height: terminal rows available.
        seed:   RNG seed for deterministic layout.
        margin: padding in columns/rows from the grid edge.

    Returns:
        (nodes, edges) — both lists are newly allocated each call.
    """
    if len(G) == 0:
        return [], []

    pos = nx.spring_layout(G, seed=seed)  # dict node → np.array([x, y])

    # Normalise from [-1, 1] (approx) to [margin, width-margin) × [margin, height-margin)
    xs = [v[0] for v in pos.values()]
    ys = [v[1] for v in pos.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = (x_max - x_min) or 1.0
    y_range = (y_max - y_min) or 1.0

    usable_w = width - 2 * margin
    usable_h = height - 2 * margin

    def _project(x: float, y: float) -> tuple[int, int]:
        col = margin + int((x - x_min) / x_range * usable_w)
        row = margin + int((y - y_min) / y_range * usable_h)
        col = max(margin, min(width - margin - 1, col))
        row = max(margin, min(height - margin - 1, row))
        return col, row

    coord: dict[str, tuple[int, int]] = {}
    nodes: list[GridNode] = []
    for node_id, (x, y) in pos.items():
        col, row = _project(x, y)
        coord[node_id] = (col, row)
        attrs = G.nodes[node_id]
        nodes.append(GridNode(
            node_id=str(node_id),
            col=col,
            row=row,
            label=attrs.get("label", str(node_id)),
            kind=attrs.get("kind", "host"),
        ))

    edges: list[EdgePath] = []
    for u, v, edata in G.edges(data=True):
        sc, sr = coord[u]
        dc, dr = coord[v]
        edges.append(EdgePath(
            src_id=str(u), dst_id=str(v),
            src_col=sc, src_row=sr,
            dst_col=dc, dst_row=dr,
            relation=edata.get("relation", ""),
        ))

    return nodes, edges
