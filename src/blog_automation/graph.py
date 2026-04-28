"""Costruzione del grafo LangGraph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes.deploy import deploy_node
from .nodes.generate import generate_node
from .nodes.link_rag import link_rag_node
from .nodes.scrape import scrape_node
from .nodes.select_topics import select_topics_node
from .nodes.seo import seo_node
from .state import PipelineState


def build_graph():
    g = StateGraph(PipelineState)

    g.add_node("scrape", scrape_node)
    g.add_node("select_topics", select_topics_node)
    g.add_node("generate", generate_node)
    g.add_node("link_rag", link_rag_node)
    g.add_node("seo", seo_node)
    g.add_node("deploy", deploy_node)

    g.add_edge(START, "scrape")
    g.add_edge("scrape", "select_topics")
    g.add_edge("select_topics", "generate")
    g.add_edge("generate", "link_rag")
    g.add_edge("link_rag", "seo")
    g.add_edge("seo", "deploy")
    g.add_edge("deploy", END)

    return g.compile()
