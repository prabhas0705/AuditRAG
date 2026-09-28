# AuditRAG

![CI](https://github.com/prabhas0705/AuditRAG/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Deterministic multi-hop compliance and evidence engine over legal/regulatory documents.
Zero pip dependencies — pure Python stdlib.

```
git clone https://github.com/prabhas0705/AuditRAG.git
cd AuditRAG
pip install .
cp .env.example .env   # add Groq key for LLM synthesis (optional)
auditrag               # starts the REPL
```

```
AuditRAG > load contracts/
  loaded 9 documents

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

1. **indexer.py** — BM25 inverted index with champion-list pruning and suffix stemming
2. **planner.py** — A\* search over a clause-adjacency graph to assemble multi-hop evidence chains
3. **router.py** — UCB1 contextual bandit that picks the cheapest model capable of the query
4. **engine.py** — Orchestrates the three above; emits a grounded audit memorandum with provenance citations

Every claim in the output is bound to a source chunk (`[file.txt#p12]`). If the evidence isn't there, it says so.

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

## Benchmark (SEC EDGAR, 9 material contracts)

| metric | value |
|---|---|
| Recall@3 | 100% |
| MRR | 0.79 |
| Fact grounding | 90.6% |
| Hallucination rate | 0% |
| Pip dependencies | 0 |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The only hard rule: no pip dependencies.

## License

MIT — [Prabhas Chirala](https://github.com/prabhas0705)
