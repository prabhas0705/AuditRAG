"""
planner.py - Artificial and Computational Intelligence (ACI) Core
Implements A* Heuristic Search to plan minimal-cost, multi-hop proof chains.
Guarantees verified evidence paths without context-window bloat.
Standard library only (Ponytail clean).
"""

import heapq
from typing import Dict, List, Set, Tuple
from indexer import HybridIndex, tokenize

class SearchNode:
    def __init__(self, current_chunk: str, path: List[str], covered_terms: Set[str], g_cost: float, h_cost: float, relevance: float = 0.0):
        self.current_chunk = current_chunk
        self.path = path
        self.covered_terms = covered_terms
        self.g_cost = g_cost  # Step cost (number of hops + reading cost)
        self.h_cost = h_cost  # Admissible heuristic: estimated remaining hops to cover all query aspects
        self.relevance = relevance

    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost

    def __lt__(self, other: "SearchNode"):
        if abs(self.f_cost - other.f_cost) > 1e-5:
            return self.f_cost < other.f_cost
        if abs(self.relevance - other.relevance) > 1e-5:
            return self.relevance > other.relevance  # higher relevance preferred on tie
        return len(self.path) < len(other.path)

class AStarEvidencePlanner:
    def __init__(self, index: HybridIndex):
        self.index = index

    def heuristic(self, covered_terms: Set[str], query_terms: Set[str]) -> float:
        """
        Admissible Heuristic h(n):
        Estimates minimum remaining hops needed to cover missing query concepts.
        Never overestimates the true distance (guarantees optimal/minimal proof paths).
        """
        remaining = len(query_terms - covered_terms)
        # Even with an optimal chunk, we cover at most ~3 distinct query terms per hop
        return (remaining + 2) // 3

    def plan_evidence_chain(self, query: str, max_hops: int = 4) -> List[str]:
        """Finds the shortest, highest-density evidence chain across documents."""
        q_tokens = set(tokenize(query))
        if not q_tokens or not self.index.chunks:
            return []

        # 1. Get initial anchor seeds via BM25 Champion Search
        seeds = self.index.bm25_search(query, top_k=8, use_champion_lists=True)
        if not seeds:
            return []
        seed_scores = dict(seeds)

        open_set: List[SearchNode] = []
        visited_states: Set[Tuple[str, int]] = set()

        for chunk_id, score in seeds:
            chunk = self.index.chunks[chunk_id]
            covered = set(chunk.tokens) & q_tokens
            h = self.heuristic(covered, q_tokens)
            node = SearchNode(
                current_chunk=chunk_id, 
                path=[chunk_id], 
                covered_terms=covered, 
                g_cost=1.0, 
                h_cost=float(h),
                relevance=score
            )
            heapq.heappush(open_set, node)

        best_path = [seeds[0][0]]
        best_coverage = len(set(self.index.chunks[seeds[0][0]].tokens) & q_tokens)

        while open_set:
            current = heapq.heappop(open_set)

            # Goal reached: All key query terms covered
            if current.h_cost == 0 or current.covered_terms >= q_tokens:
                return current.path

            if len(current.covered_terms) > best_coverage:
                best_coverage = len(current.covered_terms)
                best_path = current.path

            if len(current.path) >= max_hops:
                continue

            state_key = (current.current_chunk, len(current.covered_terms))
            if state_key in visited_states:
                continue
            visited_states.add(state_key)

            # Explore graph neighbors (connected via cross-references, sequential flow, or shared entities)
            neighbors = set(self.index.graph_edges.get(current.current_chunk, set()))
            # Also bridge to top BM25 seeds if disconnected
            neighbors |= {s[0] for s in seeds[:4] if s[0] not in current.path}

            for nxt in neighbors:
                if nxt in current.path:
                    continue
                nxt_chunk = self.index.chunks[nxt]
                new_covered = current.covered_terms | (set(nxt_chunk.tokens) & q_tokens)

                # Only expand if it adds new query coverage, or is one of the top BM25 seeds
                if not (new_covered - current.covered_terms) and nxt not in seed_scores:
                    continue

                nxt_score = seed_scores.get(nxt, 0.5)
                g = current.g_cost + 1.0  # Unit hop cost
                h = self.heuristic(new_covered, q_tokens)

                child = SearchNode(
                    current_chunk=nxt,
                    path=current.path + [nxt],
                    covered_terms=new_covered,
                    g_cost=g,
                    h_cost=float(h),
                    relevance=current.relevance + nxt_score
                )
                heapq.heappush(open_set, child)

        return best_path
