import networkx as nx
import matplotlib.pyplot as plt

# Create a directed graph
G = nx.DiGraph()

# Add Nodes
# Teal: Source Documents
G.add_node("solar_data.csv", color="teal", label="solar_data.csv\n(Source Document)")
G.add_node("market_report.pdf", color="teal", label="market_report.pdf\n(Source Document)")
G.add_node("competitor_site.html", color="teal", label="competitor_site.html\n(Web Page)")

# Orange: Extracted Context Chunks
G.add_node("chunk_1", color="orange", label="Chunk 1: Q1 Revenue Data\n(Extracted Context)")
G.add_node("chunk_2", color="orange", label="Chunk 2: Solar Efficiency\n(Extracted Context)")
G.add_node("chunk_3", color="orange", label="Chunk 3: Clean Energy Trends\n(Extracted Context)")

# Red: Blocked Dynamic Injection Payloads
G.add_node("injection_1", color="red", label="Injection Payload:\n'Ignore previous rules...'\n(Blocked)")

# Green: Inferred Claims
G.add_node("claim_1", color="green", label="Claim: Revenue grew 15%\n(Uncertainty: 0.05)")
G.add_node("claim_2", color="green", label="Claim: Efficiency increased\n(Uncertainty: 0.12)")

# Add Edges
# Document to Chunk (CONTAINS)
G.add_edge("solar_data.csv", "chunk_1", label="CONTAINS")
G.add_edge("market_report.pdf", "chunk_2", label="CONTAINS")
G.add_edge("competitor_site.html", "chunk_3", label="CONTAINS")

# The competitor site contained an injection that was blocked
G.add_edge("competitor_site.html", "injection_1", label="CONTAINS_MALICIOUS")

# Chunk to Claim (SUPPORTED_BY)
G.add_edge("chunk_1", "claim_1", label="SUPPORTED_BY")
G.add_edge("chunk_2", "claim_2", label="SUPPORTED_BY")
G.add_edge("chunk_3", "claim_2", label="SUPPORTED_BY")

# Draw the graph
plt.figure(figsize=(14, 10))

# Custom Layout to position them logically
# Sources at bottom, chunks in middle, claims at top
pos = {
    "solar_data.csv": (0, 0),
    "market_report.pdf": (1, 0),
    "competitor_site.html": (2, 0),
    
    "chunk_1": (0, 1),
    "chunk_2": (1, 1),
    "chunk_3": (2, 1),
    
    "injection_1": (3, 0.5), # Blocked injection off to the side
    
    "claim_1": (0.5, 2),
    "claim_2": (1.5, 2)
}

colors = [G.nodes[n]['color'] for n in G.nodes]
labels = {n: G.nodes[n]['label'] for n in G.nodes}

nx.draw(G, pos, with_labels=True, labels=labels, node_color=colors, node_size=5000, font_size=8, font_weight="bold", arrows=True, arrowsize=20, node_shape="s")

edge_labels = nx.get_edge_attributes(G, 'label')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

plt.title("Aegis Research OS: Evidence & Provenance Graph", fontsize=16)
plt.axis('off')
plt.savefig("evidence_map.png", format="png", dpi=300, bbox_inches="tight")
print("Saved evidence_map.png successfully.")
