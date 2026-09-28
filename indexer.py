"""
indexer.py - Information Retrieval (IR) Core
Implements Inverted Index, BM25 scoring, Champion Lists, and Section Link Graphs.
Standard library only (Ponytail clean - zero bloat).
"""

import math
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", 
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", 
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", 
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", 
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", 
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", 
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", 
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", 
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

def stem(word: str) -> str:
    """Minimal, robust suffix stemmer for English legal/IR text."""
    w = word.lower()
    if len(w) <= 3:
        return w
    for suffix, replacement in [
        ("ational", "ate"), ("tional", "tion"), ("ization", "ize"),
        ("ations", "ate"), ("ation", "ate"), ("ments", ""),
        ("ment", ""), ("abilities", "able"), ("ability", "able"),
        ("ties", "ty"), ("ies", "y"),
        ("ingly", ""), ("fully", ""), ("lessly", ""),
        ("ing", ""), ("ed", ""), ("es", ""), ("s", "")
    ]:
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[:-len(suffix)] + replacement
            break
    if len(w) >= 4 and w[-1] == w[-2] and w[-1] not in "lsz":
        w = w[:-1]
    return w

def tokenize(text: str) -> List[str]:
    """Tokenize, lowercase, filter stopwords, and stem."""
    tokens = re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())
    return [stem(t) for t in tokens if t not in STOPWORDS]

LEGAL_ENTITY_STOPWORDS = {
    "Document", "Company", "Contract", "Title", "Type", "Source", "Edgar",
    "Section", "Article", "Clause", "Exhibit", "Schedule", "Agreement",
    "Notice", "Paragraph", "Part", "General", "Terms", "Conditions",
    "Date", "Dated", "Name", "Number", "Page", "State", "States",
    "United", "Law", "Laws", "Act", "Plan", "Code", "Table", "Contents",
    "The", "This", "That", "These", "Those", "All", "Any", "Such", "Each",
    "Executive", "Employee", "Employer", "Officer", "Director", "Board",
    "Shall", "Will", "May", "Must", "Have", "Has", "Had", "Been", "Being",
    "Form", "Item", "Items", "Report", "Period", "Annual", "Quarterly",
    "Under", "With", "From", "Into", "Other", "Without", "Which", "Where"
}

class Chunk:
    def __init__(self, chunk_id: str, doc_name: str, content: str, section: str = ""):
        self.chunk_id = chunk_id
        self.doc_name = doc_name
        self.content = content
        self.section = section
        self.tokens = tokenize(content)
        # Extract named entities / capitalized anchor terms excluding boilerplate legal stopwords
        raw_entities = set(re.findall(r"\b[A-Z][a-zA-Z0-9_]{2,}\b", content))
        self.entities = {e for e in raw_entities if e not in LEGAL_ENTITY_STOPWORDS and len(e) > 3}

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "doc_name": self.doc_name,
            "section": self.section,
            "content": self.content,
            "entities": list(self.entities)
        }

class HybridIndex:
    def __init__(self, k1: float = 1.5, b: float = 0.75, champion_limit: int = 15):
        self.chunks: Dict[str, Chunk] = {}
        self.postings: Dict[str, Dict[str, int]] = defaultdict(dict)  # term -> {chunk_id: tf}
        self.champion_lists: Dict[str, List[str]] = {}  # term -> top chunk_ids
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_len = 0.0
        self.k1 = k1
        self.b = b
        self.champion_limit = champion_limit
        self.graph_edges: Dict[str, Set[str]] = defaultdict(set)  # chunk_id -> connected chunk_ids

    def add_chunk(self, chunk_id: str, doc_name: str, text: str, section: str = ""):
        chunk = Chunk(chunk_id, doc_name, text, section)
        self.chunks[chunk_id] = chunk
        self.doc_lengths[chunk_id] = len(chunk.tokens)

        # Build inverted postings
        tf_map = defaultdict(int)
        for t in chunk.tokens:
            tf_map[t] += 1
        for t, freq in tf_map.items():
            self.postings[t][chunk_id] = freq

    def finalize(self):
        """Precompute BM25 weights, Champion Lists, and cross-chunk graph relationships."""
        N = len(self.chunks)
        if N == 0:
            return
        self.avg_doc_len = sum(self.doc_lengths.values()) / N

        # 1. Build Champion Lists for fast ranked pruning (IR Chapter 6)
        for term, postings_dict in self.postings.items():
            df = len(postings_dict)
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            scored = []
            for cid, tf in postings_dict.items():
                denom = tf + self.k1 * (1 - self.b + self.b * (self.doc_lengths[cid] / self.avg_doc_len))
                score = idf * (tf * (self.k1 + 1)) / (denom if denom > 0 else 1.0)
                scored.append((cid, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            self.champion_lists[term] = [x[0] for x in scored[:self.champion_limit]]

        # 2. Build Entity/Section Graph Edges (connecting chunks that share rare entities or cross-references)
        entity_to_chunks = defaultdict(set)
        for cid, chunk in self.chunks.items():
            for ent in chunk.entities:
                entity_to_chunks[ent].add(cid)

        # ponytail: connect chunks sharing entities (min 2, max 12 to avoid god-node noise)
        for ent, cids in entity_to_chunks.items():
            if 1 < len(cids) <= 12:
                cid_list = list(cids)
                for i in range(len(cid_list)):
                    for j in range(i + 1, len(cid_list)):
                        self.graph_edges[cid_list[i]].add(cid_list[j])
                        self.graph_edges[cid_list[j]].add(cid_list[i])

        # 3. Build Sequential Document Adjacency Edges (connecting consecutive chunks in the same document)
        doc_chunks = defaultdict(list)
        for cid in self.chunks:
            doc_name = self.chunks[cid].doc_name
            doc_chunks[doc_name].append(cid)

        for doc_name, cids in doc_chunks.items():
            for i in range(len(cids) - 1):
                self.graph_edges[cids[i]].add(cids[i+1])
                self.graph_edges[cids[i+1]].add(cids[i])

    def bm25_search(self, query: str, top_k: int = 10, use_champion_lists: bool = True) -> List[Tuple[str, float]]:
        """Fast BM25 scored search over index."""
        q_tokens = tokenize(query)
        N = len(self.chunks)
        if N == 0 or not q_tokens:
            return []

        scores = defaultdict(float)
        candidate_chunks: Set[str] = set()

        for t in q_tokens:
            if use_champion_lists and t in self.champion_lists:
                candidate_chunks.update(self.champion_lists[t])
            elif t in self.postings:
                candidate_chunks.update(self.postings[t].keys())

        for t in q_tokens:
            if t not in self.postings:
                continue
            postings_dict = self.postings[t]
            df = len(postings_dict)
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

            for cid in candidate_chunks:
                if cid in postings_dict:
                    tf = postings_dict[cid]
                    denom = tf + self.k1 * (1 - self.b + self.b * (self.doc_lengths[cid] / self.avg_doc_len))
                    scores[cid] += idf * (tf * (self.k1 + 1)) / (denom if denom > 0 else 1.0)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def to_dict(self) -> Dict:
        """Serializes precomputed index state for instant disk caching."""
        return {
            "avg_doc_len": self.avg_doc_len,
            "k1": self.k1,
            "b": self.b,
            "champion_limit": self.champion_limit,
            "doc_lengths": self.doc_lengths,
            "champion_lists": self.champion_lists,
            "graph_edges": {cid: list(edges) for cid, edges in self.graph_edges.items()},
            "postings": self.postings,
            "chunks": {
                cid: {
                    "chunk_id": c.chunk_id,
                    "doc_name": c.doc_name,
                    "content": c.content,
                    "section": c.section,
                    "tokens": c.tokens
                } for cid, c in self.chunks.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HybridIndex":
        """Reconstructs HybridIndex instantly from cached dictionary without re-tokenizing."""
        idx = cls(
            k1=data.get("k1", 1.5),
            b=data.get("b", 0.75),
            champion_limit=data.get("champion_limit", 15)
        )
        idx.avg_doc_len = data.get("avg_doc_len", 0.0)
        idx.doc_lengths = data.get("doc_lengths", {})
        idx.champion_lists = data.get("champion_lists", {})
        idx.graph_edges = {cid: set(edges) for cid, edges in data.get("graph_edges", {}).items()}
        idx.postings = data.get("postings", {})

        for cid, cdata in data.get("chunks", {}).items():
            chunk = Chunk.__new__(Chunk)
            chunk.chunk_id = cdata["chunk_id"]
            chunk.doc_name = cdata["doc_name"]
            chunk.content = cdata["content"]
            chunk.section = cdata.get("section", "")
            chunk.tokens = cdata.get("tokens", [])
            chunk.entities = set()
            idx.chunks[cid] = chunk

        return idx

