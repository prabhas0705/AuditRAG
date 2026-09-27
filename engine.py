"""
engine.py - The Core AuditRAG System
Orchestrates IR indexing, ACI graph planning, and DRL bandit routing.
Works offline out-of-the-box (extractive synthesis) or connects to Gemini/OpenAI if API keys exist.
Standard library only (Ponytail clean).
"""

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple
from indexer import HybridIndex
from planner import AStarEvidencePlanner
from router import BanditModelRouter

def _load_env_file():
    """Lightweight stdlib-only .env reader (zero external pip dependencies)."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

class AuditRAG:
    def __init__(self):
        self.index = HybridIndex()
        self.planner: Optional[AStarEvidencePlanner] = None
        self.router = BanditModelRouter()
        self.ingested_files: List[str] = []

    def ingest_text(self, doc_name: str, text: str):
        """Chunks and indexes arbitrary text."""
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        for i, p in enumerate(paragraphs):
            # Extract possible section header
            section = ""
            lines = p.split("\n")
            if lines[0].startswith(("#", "Section", "Clause", "Chapter", "Article")):
                section = lines[0].strip("# ").strip()

            chunk_id = f"{doc_name}#p{i+1}"
            self.index.add_chunk(chunk_id=chunk_id, doc_name=doc_name, text=p, section=section)

    def _extract_pdf_text(self, filepath: str) -> str:
        """Extracts text from a PDF using fitz (PyMuPDF) or pypdf."""
        text = ""
        try:
            import fitz
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text("text") + "\n\n"
            if text.strip():
                return text
        except Exception:
            pass

        try:
            import pypdf
            reader = pypdf.PdfReader(filepath)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n\n"
            if text.strip():
                return text
        except Exception:
            pass
        return text

    def ingest_directory(self, folder_path: str, extensions: Tuple = (".md", ".txt", ".pdf")):
        """Recursively ingests documents from a directory (.md, .txt, .pdf)."""
        if not os.path.exists(folder_path):
            print(f"[!] Directory not found: {folder_path}")
            return 0

        count = 0
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(extensions):
                    filepath = os.path.join(root, file)
                    try:
                        if file.lower().endswith(".pdf"):
                            text = self._extract_pdf_text(filepath)
                        else:
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                text = f.read()
                        
                        if text and text.strip():
                            self.ingest_text(doc_name=file, text=text)
                            self.ingested_files.append(file)
                            count += 1
                    except Exception as e:
                        print(f"  [!] Skipped {file}: {e}")

        self.index.finalize()
        self.planner = AStarEvidencePlanner(self.index)
        return count

    def _get_omni_or_openrouter_key(self) -> Optional[str]:
        """Discovers OmniRoute gateway key or fallback keys."""
        return os.getenv("OMNIROUTE_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    def call_omni_api(self, prompt: str, selected_arm: str = "fast_flash") -> Optional[str]:
        """Calls local OmniRoute gateway (http://localhost:20128) using stdlib urllib."""
        key = self._get_omni_or_openrouter_key()
        if not key:
            return None
        
        # Model routing through OmniRoute
        model = "auto/best-reasoning" if selected_arm == "deep_reasoner" else "auto/best-fast"
        endpoint = "http://localhost:20128/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://auditrag.local",
            "X-Title": "AuditRAG"
        }
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1024
        }).encode("utf-8")

        try:
            req = urllib.request.Request(endpoint, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                elif "content" in data and len(data["content"]) > 0:
                    return data["content"][0]["text"]
        except Exception as e:
            # If local OmniRoute combo fails or is offline, fall through to deterministic offline extraction
            return None

    def call_gemini_api(self, prompt: str, model: str = "gemini-1.5-flash") -> Optional[str]:
        """Calls Gemini API using raw stdlib urllib (zero pip install dependencies)."""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024}
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return None

    def call_groq_api(self, prompt: str, selected_arm: str = "fast_flash") -> Optional[str]:
        """Calls Groq API (ultra-fast, 100% free Qwen-27B) using stdlib urllib."""
        key = os.getenv("GROQ_API_KEY")
        if not key:
            return None

        model = "qwen/qwen3.8-27b"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1024
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
        except Exception:
            return None
        return None

    def query(self, user_query: str) -> Dict:
        """Executes full Search-as-Planning multi-hop retrieval and audited response generation."""
        if not self.planner or not self.index.chunks:
            return {
                "error": "No documents ingested. Please ingest files or a directory first."
            }

        # 1. ACI A* Search plans the evidence chain across cross-document links
        proof_chain = self.planner.plan_evidence_chain(user_query, max_hops=3)

        # 2. DRL Bandit Router selects optimal model tier
        selected_arm, rationale = self.router.select_arm(user_query, hops_needed=len(proof_chain))

        # 3. Assemble evidence context
        evidence_items = []
        context_blocks = []
        for step, cid in enumerate(proof_chain, 1):
            chunk = self.index.chunks[cid]
            evidence_items.append({
                "hop": step,
                "chunk_id": cid,
                "doc_name": chunk.doc_name,
                "section": chunk.section,
                "content": chunk.content
            })
            context_blocks.append(f"[{cid}] (from {chunk.doc_name}):\n{chunk.content}")

        context_str = "\n\n---\n\n".join(context_blocks)

        # 4. LLM Generation: Groq Free -> OmniRoute Gateway -> Gemini -> Deterministic Extraction
        import datetime
        current_date_str = datetime.date.today().strftime("%B %d, %Y")
        prompt = (
            f"You are AuditRAG Enterprise, an institutional-grade General Counsel and Senior Regulatory Compliance Auditor.\n"
            f"Deliver an exhaustive, forensic executive audit addressing the inquiry strictly and exclusively from the examined evidentiary record below.\n\n"
            f"Institutional Audit Guidelines:\n"
            f"1. Header Structure:\n"
            f"**EXECUTIVE AUDIT MEMORANDUM**\n\n"
            f"**TO:** Board of Directors / Senior Governance\n"
            f"**FROM:** AuditRAG Enterprise — General Counsel & Senior Regulatory Compliance Auditor\n"
            f"**RE:** Forensic Compliance Audit: {user_query}\n"
            f"**DATE:** {current_date_str}\n\n"
            f"2. Organization: Present findings under standard legal diligence headings: '### I. EXECUTIVE OPINION & SUMMARY', '### II. STATUTORY & CONTRACTUAL FINDINGS', and '### III. PROVENANCE VERIFICATION'.\n"
            f"3. Strict Grounding: For every material assertion, covenant citation, and factual finding, affix the exact provenance chunk ID (e.g. [Document.txt#pX]).\n"
            f"4. Zero Speculation Mandate: If a specific clause, threshold, or reporting line is not established in the examined instruments, state explicitly and unequivocally: 'Not stated in examined record'. Do not extrapolate.\n"
            f"5. Tone: Rigorous, institutional, and boardroom-ready.\n\n"
            f"EXAMINED INSTRUMENTS & PROVENANCE RECORD:\n{context_str}\n\n"
            f"INQUIRY / AUDIT MANDATE: {user_query}\n\n"
            f"EXECUTIVE AUDIT MEMORANDUM:\n"
        )

        # Priority 1: Groq Free API (100% Free, ultra-fast Qwen 27B)
        llm_response = self.call_groq_api(prompt, selected_arm=selected_arm)

        # Priority 2: OmniRoute Gateway
        if not llm_response:
            llm_response = self.call_omni_api(prompt, selected_arm=selected_arm)

        # Priority 3: Gemini API
        if not llm_response:
            model_name = "gemini-1.5-pro" if selected_arm == "deep_reasoner" else "gemini-1.5-flash"
            llm_response = self.call_gemini_api(prompt, model=model_name)

        # Priority 4: Deterministic offline extraction
        if not llm_response:
            llm_response = (
                f"### CERTIFIED EVIDENCE PROVENANCE RECORD ({len(proof_chain)} Admissible Hops):\n\n"
                + "\n\n".join([f"**Provenance Hop {item['hop']} • [{item['chunk_id']}]** ({item['doc_name']}):\n> {item['content']}" for item in evidence_items])
                + f"\n\n*(Notice: Enclave offline extraction operational. Connect Groq/OmniRoute endpoint for autonomous natural language synthesis.)*"
            )

        # Update bandit reward based on proof chain quality (1.0 for valid grounding, 0.5 for partial)
        self.router.update(selected_arm, accuracy_score=1.0 if proof_chain else 0.0, token_cost_cents=0.2 if selected_arm == "fast_flash" else 1.0)

        return {
            "query": user_query,
            "router_tier": selected_arm,
            "router_rationale": rationale,
            "proof_chain_length": len(proof_chain),
            "evidence": evidence_items,
            "audit_response": llm_response,
            "graph_summary": {
                "total_indexed_chunks": len(self.index.chunks),
                "total_graph_connections": sum(len(v) for v in self.index.graph_edges.values()) // 2
            }
        }
