"""graph_layout pure-function tests. No TUI required."""
import networkx as nx
import pytest
from bagley.tui.services.graph_layout import layout_to_grid, EdgePath, GridNode


def _simple_graph() -> nx.Graph:
    G = nx.Graph()
    G.add_node("A", label="10.10.14.1", kind="host")
    G.add_node("B", label="10.10.14.2", kind="host")
    G.add_node("C", label="10.10.14.3", kind="host")
    G.add_edge("A", "B", relation="scanned")
    G.add_edge("B", "C", relation="pivoted")
    return G


def test_layout_returns_grid_nodes_for_all_nodes():
    G = _simple_graph()
    nodes, edges = layout_to_grid(G, width=80, height=24)
    node_ids = {n.node_id for n in nodes}
    assert node_ids == {"A", "B", "C"}


def test_layout_coords_within_grid_bounds():
    G = _simple_graph()
    nodes, _ = layout_to_grid(G, width=80, height=24)
    for n in nodes:
        assert 0 <= n.col < 80, f"col={n.col} out of range"
        assert 0 <= n.row < 24, f"row={n.row} out of range"


def test_layout_edges_list_matches_graph_edges():
    G = _simple_graph()
    _, edges = layout_to_grid(G, width=80, height=24)
    edge_pairs = {(e.src_id, e.dst_id) for e in edges}
    assert ("A", "B") in edge_pairs or ("B", "A") in edge_pairs
    assert ("B", "C") in edge_pairs or ("C", "B") in edge_pairs


def test_layout_single_node():
    G = nx.Graph()
    G.add_node("solo", label="192.168.1.1", kind="host")
    nodes, edges = layout_to_grid(G, width=40, height=20)
    assert len(nodes) == 1
    assert len(edges) == 0


def test_layout_is_deterministic_with_seed():
    G = _simple_graph()
    nodes_a, _ = layout_to_grid(G, width=80, height=24, seed=42)
    nodes_b, _ = layout_to_grid(G, width=80, height=24, seed=42)
    pos_a = {n.node_id: (n.col, n.row) for n in nodes_a}
    pos_b = {n.node_id: (n.col, n.row) for n in nodes_b}
    assert pos_a == pos_b
