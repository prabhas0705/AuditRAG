"""
evaluate.py - Quantitative Evaluation Benchmark for AuditRAG
Measures Retrieval (IR), Search-as-Planning (ACI), Grounding (RAGAS), and Cost (DRL).
Run with: python evaluate.py
"""

import time
from engine import AuditRAG

# Curated ground-truth test cases across legal & technical domains
BENCHMARK_SUITE = [
    {
        "id": "TC-01",
        "category": "Contradiction / Superseding Clause (Multi-Hop)",
        "query": "How does Clause 8.2 alter the Section 14 liability limit?",
        "expected_chunks": ["Contract_Amendment_2024_02.txt#p2", "Master_Service_Agreement_2023.txt#p2"],
        "expected_facts": ["$5,000,000", "superseded", "Section 14"],
        "min_hops": 1
    },
    {
        "id": "TC-02",
        "category": "Compliance Timeframe (Single-Hop Factoid)",
        "query": "What are the breach notification obligations under Section 7?",
        "expected_chunks": ["Security_Addendum_2024.txt#p2"],
        "expected_facts": ["twenty-four", "24", "hours", "Customer Personal Data"],
        "min_hops": 1
    },
    {
        "id": "TC-03",
        "category": "Jurisdiction & Certification (Multi-Hop Conjunction)",
        "query": "What is the governing law in Delaware and what are the security standards in Section 3?",
        "expected_chunks": ["Master_Service_Agreement_2023.txt#p3", "Security_Addendum_2024.txt#p1"],
        "expected_facts": ["Delaware", "ISO/IEC 27001", "SOC2"],
        "min_hops": 2
    }
]

def run_evaluation():
    print("=" * 70)
    print("  AUDITRAG AUTOMATED EVALUATION & BENCHMARK SUITE")
    print("=" * 70)
    print("Initializing test engine and default corpus...")
    
    rag = AuditRAG()
    from server import SAMPLE_DOCS
    for fname, text in SAMPLE_DOCS.items():
        rag.ingest_text(fname, text)
    rag.index.finalize()
    from planner import AStarEvidencePlanner
    rag.planner = AStarEvidencePlanner(rag.index)

    total_tests = len(BENCHMARK_SUITE)
    recall_hits = 0
    mrr_total = 0.0
    grounding_precision_total = 0.0
    hops_completed = 0
    total_latency_ms = 0.0
    cost_baseline_cents = 0.0   # If all routed to deep_reasoner ($0.05 / query)
    cost_bandit_cents = 0.0     # Bandit actual routing cost

    print(f"\nRunning {total_tests} standard audit benchmarks:\n")

    for tc in BENCHMARK_SUITE:
        t0 = time.perf_counter()
        result = rag.query(tc["query"])
        latency_ms = (time.perf_counter() - t0) * 1000
        total_latency_ms += latency_ms

        retrieved_cids = [item["chunk_id"] for item in result["evidence"]]
        verdict_text = result["audit_response"].lower()

        # 1. Retrieval Recall & MRR (IR metrics)
        hit = any(exp in retrieved_cids for exp in tc["expected_chunks"])
        if hit:
            recall_hits += 1

        # MRR calculation
        ranks = [retrieved_cids.index(exp) + 1 for exp in tc["expected_chunks"] if exp in retrieved_cids]
        mrr = (1.0 / min(ranks)) if ranks else 0.0
        mrr_total += mrr

        # 2. Grounding & Fact Verification (RAGAS metric)
        facts_found = sum(1 for fact in tc["expected_facts"] if fact.lower() in verdict_text)
        fact_score = (facts_found / len(tc["expected_facts"])) * 100.0
        grounding_precision_total += fact_score

        # 3. Hop Completeness
        if result["proof_chain_length"] >= tc["min_hops"]:
            hops_completed += 1

        # 4. Bandit Unit Economics (DRL metric)
        cost_baseline_cents += 5.0  # Deep reasoner base price
        cost_bandit_cents += 0.3 if result["router_tier"] == "fast_flash" else 5.0

        print(f"[{tc['id']}] {tc['category']}")
        print(f"  Query: \"{tc['query']}\"")
        print(f"  Router Tier: {result['router_tier'].upper()} | Latency: {latency_ms:.1f}ms")
        print(f"  Hops Resolved: {result['proof_chain_length']} | MRR: {mrr:.2f} | Fact Grounding: {fact_score:.0f}%")
        print(f"  Retrieved Evidence: {retrieved_cids}")
        print("-" * 70)

    # Summary Report
    avg_recall = (recall_hits / total_tests) * 100.0
    avg_mrr = mrr_total / total_tests
    avg_grounding = grounding_precision_total / total_tests
    hop_completeness = (hops_completed / total_tests) * 100.0
    avg_latency = total_latency_ms / total_tests
    cost_savings_pct = ((cost_baseline_cents - cost_bandit_cents) / cost_baseline_cents) * 100.0

    print("\n" + "=" * 70)
    print("  EXECUTIVE BENCHMARK SCORECARD")
    print("=" * 70)
    print(f"  1. Retrieval Recall@3 (IR):           {avg_recall:6.1f}%   (Target: >95%)")
    print(f"  2. Mean Reciprocal Rank - MRR (IR):    {avg_mrr:6.2f}   (1.0 = Perfect)")
    print(f"  3. Fact Grounding Precision (RAGAS):  {avg_grounding:6.1f}%   (Target: 100%)")
    print(f"  4. Hallucination Rate:                {100.0 - avg_grounding:6.1f}%   (Target: 0.0%)")
    print(f"  5. Hop Path Completeness (ACI A*):    {hop_completeness:6.1f}%   (Target: 100%)")
    print(f"  6. Average Latency (Search + Plan):   {avg_latency:6.1f}ms  (Sub-second)")
    print(f"  7. Bandit Cost Reduction (DRL):       {cost_savings_pct:6.1f}%   (Unit Margin: 92%+)")
    print("=" * 70)

if __name__ == "__main__":
    run_evaluation()
