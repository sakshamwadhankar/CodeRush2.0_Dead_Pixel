"""
Demonstration of Step C2: Deduplication and Conflict Tracking in Aegis Research OS.
"""

import json
from retriever import HybridRAGEngine, ChunkDeduplicator, ConflictTracker


def run_c2_demo():
    print("=== Aegis Research OS - Step C2 Deduplication & Conflict Tracker ===")

    engine = HybridRAGEngine(collection_name="aegis_c2_demo")
    engine.reset()

    # Document A (Original Claims)
    doc_a = """# Specifications
The battery life of Aegis Autonomous Drone is 10 hours under normal load.

Aegis OS supports offline execution for research agents.

The communication channel status is online.
"""

    # Document B (Duplicate passage + Contradictory Claims)
    doc_b = """# Specifications Update
The battery life of Aegis Autonomous Drone is 10 hours under normal load.

The battery life of Aegis Autonomous Drone is 4 hours under normal load.

Aegis OS does not support offline execution for research agents.

The communication channel status is offline.
"""

    print("\n[1] Ingesting Research Documents A & B...")
    chunks_a = engine.ingest_document(doc_a, doc_id="doc_specs_v1")
    chunks_b = engine.ingest_document(doc_b, doc_id="doc_specs_v2")

    all_chunks = chunks_a + chunks_b
    print(f"[OK] Total ingested passage chunks: {len(all_chunks)}")

    # Step C2 - Deduplication
    print("\n[2] Running Semantic Chunk Deduplication (Threshold = 0.85)...")
    dedup_result = engine.deduplicate_passages(all_chunks)
    dedup_chunks = dedup_result["deduplicated_chunks"]
    print(f"[OK] Redundant duplicate chunks removed: {dedup_result['duplicate_count']}")
    print(f"[OK] Unique canonical chunks remaining: {len(dedup_chunks)}")

    # Step C2 - Conflict Detection
    print("\n[3] Running Conflict Tracker (Contradiction Detection)...")
    conflicts = engine.detect_conflicts(all_chunks)
    print(f"[OK] Identified {len(conflicts)} direct contradictions across retrieved statements:")

    for c in conflicts:
        print(f"\n--- [{c['conflict_id']}] Conflict Type: {c['conflict_type']} ---")
        print(f"Claim A ({c['claim_a']['source_doc_id']}): \"{c['claim_a']['statement']}\"")
        print(f"Claim B ({c['claim_b']['source_doc_id']}): \"{c['claim_b']['statement']}\"")
        print(f"Details: {c['opposing_details']}")

    # Step C2 - State Synchronization
    print("\n[4] Writing state results to state.json...")
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump({
            "project_name": "Aegis Research OS",
            "active_task_id": "task_c2_dedup_conflict",
            "query": "battery life offline execution communication status",
            "retrieval_config": {"top_k": 5, "dense_weight": 0.5, "sparse_weight": 0.5},
            "search_results": [],
            "deduplicated_results": [],
            "tracked_conflicts": [],
            "status": "idle"
        }, f, indent=2)

    updated_state = engine.sync_with_state("state.json")
    print(f"[OK] state.json status: {updated_state['status']}")
    print(f"[OK] state.json deduplicated_results count: {len(updated_state['deduplicated_results'])}")
    print(f"[OK] state.json tracked_conflicts count: {len(updated_state['tracked_conflicts'])}")

    print("\n=== Step C2 Deduplication & Conflict Tracker demo completed successfully! ===")


if __name__ == "__main__":
    run_c2_demo()
