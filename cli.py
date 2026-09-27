"""
cli.py - Command Line Interface for AuditRAG
Run: python cli.py "How does Clause 8.2 alter the Section 14 liability limit?"
Or: python cli.py --ingest "D:\\MTECH\\Semester2\\Information Retrieval\\lecture_slides_md"
"""

import sys
from engine import AuditRAG

def main():
    rag = AuditRAG()
    
    # Ingest default legal demo docs
    from server import SAMPLE_DOCS
    for fname, text in SAMPLE_DOCS.items():
        rag.ingest_text(fname, text)
    rag.index.finalize()
    from planner import AStarEvidencePlanner
    rag.planner = AStarEvidencePlanner(rag.index)

    if len(sys.argv) > 2 and sys.argv[1] == "--ingest":
        folder = sys.argv[2]
        cnt = rag.ingest_directory(folder)
        print(f"[+] Ingested {cnt} documents from {folder}")
        return

    query = sys.argv[1] if len(sys.argv) > 1 else "How does Clause 8.2 alter the Section 14 liability limit?"
    print(f"\n[*] Executing Audited Search for: '{query}'\n")

    res = rag.query(query)
    
    print("=" * 60)
    print(f"ROUTER: {res['router_tier']} | {res['router_rationale']}")
    print(f"PROOF CHAIN: {res['proof_chain_length']} hops resolved via A* Search")
    print("=" * 60)
    print("\n[VERIFIED AUDIT RESPONSE]:")
    print(res["audit_response"])
    print("\n" + "=" * 60)
    print("EVIDENCE PROOF CHAIN:")
    for item in res["evidence"]:
        print(f"\n[HOP {item['hop']}] {item['chunk_id']} ({item['doc_name']})")
        print(f"Content: {item['content']}")

if __name__ == "__main__":
    main()
