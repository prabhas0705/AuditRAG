"""
router.py - Deep Reinforcement Learning (DRL) Core
Multi-Armed Bandit (UCB1) for Adaptive LLM Routing and Token-Budget Optimization.
Maximizes Answer Precision while Minimizing API Cost.
Standard library only (Ponytail clean).
"""

import math
from typing import Dict, Tuple

class BanditModelRouter:
    def __init__(self, c: float = 1.414):
        # Arms: 0 = "fast_flash" (cheap), 1 = "deep_reasoner" (expensive)
        self.arms = ["fast_flash", "deep_reasoner"]
        self.counts: Dict[str, int] = {a: 0 for a in self.arms}
        self.values: Dict[str, float] = {a: 0.0 for a in self.arms}
        self.total_pulls = 0
        self.c = c  # Exploration constant (UCB1)
        self.total_cost_saved_usd = 0.0

    def select_arm(self, query: str, hops_needed: int) -> Tuple[str, str]:
        """
        Contextual UCB1 Selection:
        Combines empirical value, exploration bonus, and query difficulty.
        Returns: (selected_arm, rationale)
        """
        self.total_pulls += 1
        q_len = len(query.split())
        is_multihop = hops_needed > 1

        # Complexity metric: based on query length and required graph hops
        complexity = min(1.0, (q_len / 12.0) * 0.5 + (hops_needed / 3.0) * 0.5)

        # High complexity multi-hop queries strictly require deep reasoner
        if complexity > 0.65 or is_multihop:
            self.counts["deep_reasoner"] += 1
            return "deep_reasoner", f"High complexity ({complexity:.2f}) / multi-hop ({hops_needed} hops)"

        # Cold-start initialization
        for arm in self.arms:
            if self.counts[arm] == 0:
                self.counts[arm] += 1
                return arm, "Initial exploration"

        # UCB1 calculation: Q(a) + c * sqrt(ln(t) / N(a))
        best_arm = self.arms[0]
        max_ucb = -float("inf")
        for arm in self.arms:
            bonus = self.c * math.sqrt(math.log(self.total_pulls) / self.counts[arm])
            ucb = self.values[arm] + bonus
            if ucb > max_ucb:
                max_ucb = ucb
                best_arm = arm

        self.counts[best_arm] += 1
        if best_arm == "fast_flash":
            self.total_cost_saved_usd += 0.02  # saved vs expensive model
        return best_arm, f"UCB1 optimal value (Score: {max_ucb:.3f})"

    def update(self, arm: str, accuracy_score: float, token_cost_cents: float):
        """
        Reward Formulation (Sutton & Barto Eq 2.3):
        R = Accuracy - lambda * TokenCost
        """
        cost_penalty = 0.05 * token_cost_cents
        reward = accuracy_score - cost_penalty

        n = self.counts[arm]
        # Incremental sample-average update: Q_{n+1} = Q_n + (1/n) * [R - Q_n]
        self.values[arm] += (reward - self.values[arm]) / (n if n > 0 else 1)
