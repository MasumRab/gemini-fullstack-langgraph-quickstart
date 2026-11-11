import dataclasses
from typing import Dict, List, Optional, Any, Callable
import sys

@dataclasses.dataclass
class DispatchResult:
    route: str
    confidence: float
    metadata: Dict[str, Any]

class Dispatcher:
    """
    Dispatcher component that routes queries using hybrid ranking.
    """
    def __init__(
        self,
        semantic_weight: float = 0.5,
        lexical_weight: float = 0.5
    ):
        """
        Args:
            semantic_weight (float, optional): Weight for semantic score. Defaults to 0.5.
            lexical_weight (float, optional): Weight for lexical score. Defaults to 0.5.
        """
        self.semantic_weight = semantic_weight
        self.lexical_weight = lexical_weight

    def _hybrid_score(self, semantic_score: float, lexical_score: float) -> float:
        return (self.semantic_weight * semantic_score) + (self.lexical_weight * lexical_score)

    def dispatch(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> DispatchResult:
        """
        Dispatches the query by scoring candidates and picking the best one.
        Uses hybrid ranking and delegates intent selection to IntelligentDispatcher.
        
        Args:
            query (str): The input query.
            candidates (List[Dict[str, Any]]): List of candidates to route to.
                Each candidate should be a dict containing 'id' and optionally
                'semantic_score' and 'lexical_score'.
                
        Returns:
            DispatchResult: The chosen route and metadata.
        """
        if not candidates:
            return DispatchResult(route="default", confidence=0.0, metadata={})
            
        # Filter valid candidates and extract IDs properly
        valid_candidates = []
        for cand in candidates:
            cand_id = cand.get("id")
            if not isinstance(cand_id, str) or not cand_id.strip():
                continue
            valid_candidates.append(cand)
            
        if not valid_candidates:
            return DispatchResult(route="default", confidence=0.0, metadata={})

        # Defer import of the real IntelligentDispatcher
        try:
            from dspy_helm.routing.intelligent_dispatcher import IntelligentDispatcher
            dispatcher = IntelligentDispatcher()
        except ImportError:
            # For testing with mocked module
            if 'dspy_helm' in sys.modules and hasattr(sys.modules['dspy_helm'], 'routing'):
                IntelligentDispatcher = getattr(sys.modules['dspy_helm'].routing, 'intelligent_dispatcher').IntelligentDispatcher
                dispatcher = IntelligentDispatcher()
            else:
                raise RuntimeError("IntelligentDispatcher is not available in this environment. Ensure dspy_helm is installed.")
        
        # We process candidates, calculate their hybrid scores, and sort them.
        # To break ties deterministically, we sort by score (descending) and then id (ascending).
        scored_candidates = []
        for cand in valid_candidates:
            semantic = cand.get("semantic_score", 0.0)
            lexical = cand.get("lexical_score", 0.0)
            cand_id = str(cand.get("id"))
            
            score = self._hybrid_score(semantic, lexical)
            scored_candidates.append({
                "id": cand_id,
                "score": score,
                "candidate": cand
            })
            
        scored_candidates.sort(key=lambda x: (-x["score"], str(x["id"])))
        
        best_match = scored_candidates[0]
        
        # Ask IntelligentDispatcher to validate or augment the choice based on the best matched id
        intent_result = dispatcher.select_intent(query, [best_match["id"]])
        
        route = best_match["id"]
        confidence = best_match["score"]
        raw_candidate = best_match["candidate"]
        
        # Determine actual route based on intent dispatcher result
        selected_intent = None
        if isinstance(intent_result, dict) and "intent" in intent_result:
            selected_intent = intent_result.get("intent")
        elif hasattr(intent_result, 'get'):
            # Handling potential MagicMock returns
            selected_intent = intent_result.get("intent")
        elif hasattr(intent_result, 'intent'):
            selected_intent = intent_result.intent
            
        # Ensure selected route is valid string type
        if isinstance(selected_intent, str) and selected_intent:
            route = selected_intent
            
            # If IntelligentDispatcher returned a different route, update confidence and raw_candidate
            if route != best_match["id"]:
                matched_cand = next((c for c in scored_candidates if c["id"] == route), None)
                if matched_cand:
                    confidence = matched_cand["score"]
                    raw_candidate = matched_cand["candidate"]
        
        metadata = {
            "hybrid_score": confidence,
            "raw_candidate": raw_candidate,
            "intelligent_dispatcher_result": intent_result
        }
        
        return DispatchResult(
            route=route,
            confidence=confidence,
            metadata=metadata
        )

def select_best_route(query: str, options: List[Dict[str, Any]]) -> str:
    """
    Public function for legacy callers.
    """
    dispatcher = Dispatcher()
    result = dispatcher.dispatch(query, options)
    return result.route
