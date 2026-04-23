"""GraphPane rendering tests using Textual Pilot."""
import pytest
import networkx as nx
from textual.app import App, ComposeResult
from bagley.tui.panels.graph import GraphPane


class _GraphApp(App):
    def compose(self) -> ComposeResult:
        G = nx.Graph()
        G.add_node("A", label="10.10.14.1", kind="host")
        G.add_node("B", label="10.10.14.2", kind="host")
        G.add_edge("A", "B", relation="scanned")
        yield GraphPane(graph=G, current_target="A", id="graph")


@pytest.mark.asyncio
async def test_graph_pane_mounts():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        assert pane is not None


@pytest.mark.asyncio
async def test_graph_pane_renders_node_labels():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        rendered = pane.render_to_text()
        assert "10.10.14.1" in rendered or "A" in rendered


@pytest.mark.asyncio
async def test_graph_pane_marks_current_target():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        rendered = pane.render_to_text()
        # Current target is marked with star
        assert "★" in rendered


@pytest.mark.asyncio
async def test_graph_pane_update_graph_rerenders():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        G2 = nx.Graph()
        G2.add_node("X", label="192.168.1.1", kind="host")
        pane.update_graph(G2, current_target="X")
        await pilot.pause()
        rendered = pane.render_to_text()
        assert "192.168.1.1" in rendered or "X" in rendered
