# AuditRAG

![CI](https://github.com/prabhas0705/AuditRAG/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Deterministic multi-hop compliance and evidence engine over legal/regulatory documents (.pdf, .docx, .txt, .md).
Zero pip dependencies — pure Python stdlib.

```
git clone https://github.com/prabhas0705/AuditRAG.git
cd AuditRAG
pip install .
cp .env.example .env   # add Groq key for LLM synthesis (optional)
auditrag               # starts the REPL
```

```
AuditRAG > load contracts/          # loads folder with .pdf, .docx, .txt
  loaded 11 documents

AuditRAG > load Sample_Agreement.docx
  loaded Sample_Agreement.docx

AuditRAG > what are Tesla's termination rights?
  ------------------------------------------------------------
  FINDING: Tesla may terminate upon 30-day written notice...
  Citations:
    [TeslaCredit.txt#p12]  Tesla may terminate this Agreement...
  ------------------------------------------------------------

AuditRAG > quit
```

Without an API key it runs fully offline with extractive synthesis.

## How it works

1. **indexer.py** — BM25 inverted index with champion-list pruning, suffix stemming, and precomputed disk caching (`.auditrag_cache.json` loads 4,449 clauses in ~150ms)
2. **planner.py** — A\* search over a clause-adjacency graph to assemble minimal-cost, multi-hop evidence chains
3. **router.py** — UCB1 contextual bandit that picks the cheapest model capable of the query
4. **engine.py** — Orchestrates the three above; emits an institutional audit memorandum with provenance citations
5. **Zero-Hallucination Refusal Enclave** — Computes query term coverage; if core concepts are absent (< 40% grounding), it halts LLM execution and returns a Certified Negative Memorandum with 0% speculation

Every claim in the output is bound to a source chunk (`[file.txt#p12]`). If the evidence isn't there, it certifiedly refuses.

## Files

```
indexer.py             BM25 + champion lists + entity graph
planner.py             A* evidence planner
router.py              UCB1 bandit model router
engine.py              orchestrator + synthesis pipeline
server.py              web UI (single-file, no frameworks)
cli.py                 headless CLI
evaluate_sec.py        SEC EDGAR benchmark (Tesla, MSFT, Google, Apple)
fetch_sec_contracts.py EDGAR Exhibit-10 harvester
sec_corpus/            benchmark contracts
.env.example           env template
```

## Benchmark (19 Enterprise Instruments, 4,449 Clauses)

Evaluated across Google Cloud Terms, Google Play Agreement, Google TOS, SEC EDGAR Exhibit 10 filings (Tesla, Apple, Microsoft), Word (.docx), and PDF contracts:

| Metric | Result |
|---|---|
| Corpus scale | 19 instruments, 4,449 clauses (~580,000 words) |
| Provenance graph | 14,428 cross-clause & sequential edges |
| Exact Clause Recall@3 | 85.7% (exact clause level) |
| Exact Clause Recall@1 | 42.9% |
| Mean Reciprocal Rank (MRR) | 0.63 |
| Ingestion throughput | 2,449 clauses/sec (pure stdlib) |
| Hallucination rate | 0% (LLM mode) / 9.4% (offline extractive) |
| Pip dependencies | 0 |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The only hard rule: no pip dependencies.

## License

MIT — [Prabhas Chirala](https://github.com/prabhas0705)
