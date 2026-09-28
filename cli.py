"""
cli.py  —  AuditRAG interactive REPL

  python cli.py                      interactive session
  python cli.py "question"           one-shot (uses bundled demo docs)
  python cli.py --load <path>        load then enter REPL
  echo "question" | python cli.py --load path/   pipe/batch mode
"""

import os
import sys

try:
    import readline  # arrow keys + history on Linux/macOS; graceful no-op on Windows
except ImportError:
    pass

from engine import AuditRAG

BANNER = """\
AuditRAG  —  deterministic multi-hop compliance engine
  load <file-or-folder>   ingest documents (.pdf, .docx, .txt, .md)
  clear                   clear screen
  quit                    exit
Anything else is a query.\
"""

SEP = "-" * 60


def _finalize(rag):
    rag.index.finalize()
    from planner import AStarEvidencePlanner
    rag.planner = AStarEvidencePlanner(rag.index)


def _load(rag, path):
    path = path.strip()
    if not os.path.exists(path):
        print(f"  not found: {path}")
        return
    if os.path.isdir(path):
        n = rag.ingest_directory(path)
        print(f"  loaded {n} documents")
    else:
        if rag.ingest_file(path):
            print(f"  loaded {os.path.basename(path)}")
        else:
            print(f"  unable to extract text from {os.path.basename(path)}")
    _finalize(rag)


def _seed_demo(rag):
    """Fallback: load bundled demo docs so single-shot works out of the box."""
    try:
        from server import SAMPLE_DOCS
        for fname, text in SAMPLE_DOCS.items():
            rag.ingest_text(fname, text)
        _finalize(rag)
    except Exception:
        pass


def _query(rag, q):
    if rag.planner is None:
        print("  no documents loaded — use  load <path>  first")
        return
    res = rag.query(q)
    print()
    print(SEP)
    print(res["audit_response"])
    if res.get("evidence"):
        print()
        print("Citations:")
        for item in res["evidence"]:
            snippet = item["content"][:120].strip().replace("\n", " ")
            print(f"  [{item['chunk_id']}]  {snippet}")
    print(SEP)
    print()


def main():
    rag = AuditRAG()
    args = sys.argv[1:]

    # --load flag: load before doing anything else
    if "--load" in args:
        idx = args.index("--load")
        args.pop(idx)
        path = args.pop(idx) if idx < len(args) else ""
        _load(rag, path)

    # single-shot: question as CLI argument
    if args:
        if rag.planner is None:
            _seed_demo(rag)
        _query(rag, " ".join(args))
        return

    # pipe/batch mode: read queries from stdin line by line, no prompts
    if not sys.stdin.isatty():
        if rag.planner is None:
            _seed_demo(rag)
        for line in sys.stdin:
            line = line.strip()
            if line:
                _query(rag, line)
        return

    # ── interactive REPL ──────────────────────────────────────────────────────
    print(BANNER)
    print()

    while True:
        try:
            line = input("AuditRAG > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        if not line:
            continue
        if line in ("quit", "exit", "q"):
            print("bye.")
            break
        if line == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        if line.startswith("load "):
            _load(rag, line[5:])
            continue

        _query(rag, line)


if __name__ == "__main__":
    main()
