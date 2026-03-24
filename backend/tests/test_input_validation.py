import unittest
import sys
import os

# Add backend/src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from agent.app import InvokeRequest

class TestDoS(unittest.TestCase):
    def test_large_initial_query_count(self):
        """
        Verify that InvokeRequest REJECTS dangerously high values for initial_search_query_count.
        """
        # This payload attempts to set a huge number of initial queries
        payload = {
            "input": {
                "initial_search_query_count": 1000000,
                "messages": [{"role": "user", "content": "test"}]
            },
            "config": {}
        }

        # This should now RAISE ValueError
        with self.assertRaises(ValueError) as cm:
            req = InvokeRequest(**payload)

        self.assertIn("initial_search_query_count cannot exceed 10", str(cm.exception))

    def test_large_research_loops(self):
        """
        Verify that InvokeRequest REJECTS dangerously high values for max_research_loops.
        """
        payload = {
            "input": {
                "max_research_loops": 1000,
                "messages": [{"role": "user", "content": "test"}]
            },
            "config": {}
        }

        with self.assertRaises(ValueError) as cm:
            req = InvokeRequest(**payload)

        self.assertIn("max_research_loops cannot exceed 10", str(cm.exception))

    def test_valid_inputs(self):
        """
        Verify that InvokeRequest accepts reasonable values.
        """
        payload = {
            "input": {
                "initial_search_query_count": 5,
                "max_research_loops": 3,
                "messages": [{"role": "user", "content": "test"}]
            },
            "config": {}
        }
        req = InvokeRequest(**payload)
        self.assertEqual(req.input["initial_search_query_count"], 5)
        self.assertEqual(req.input["max_research_loops"], 3)

if __name__ == '__main__':
    unittest.main()
