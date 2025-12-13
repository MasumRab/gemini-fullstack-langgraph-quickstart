import unittest
from agent.memory_tools import save_plan_tool, load_plan_tool
from agent.persistence import PLAN_DIR
import os
import shutil

class TestMemoryTools(unittest.TestCase):
    def setUp(self):
        """
        Prepare test environment by ensuring the PLAN_DIR directory exists and setting the test_thread identifier.
        
        This creates PLAN_DIR if it does not already exist and assigns "test_tool_thread" to self.test_thread for use by tests.
        """
        os.makedirs(PLAN_DIR, exist_ok=True)
        self.test_thread = "test_tool_thread"

    def tearDown(self):
        # Cleanup
        """
        Remove the test plan directory and its contents if it exists.
        
        This is called after each test to clean up filesystem state by deleting the directory referenced by `PLAN_DIR`.
        """
        if os.path.exists(PLAN_DIR):
            shutil.rmtree(PLAN_DIR)

    def test_save_and_load(self):
        # Save
        result_save = save_plan_tool.invoke({
            "thread_id": self.test_thread,
            "todo_list": [{"task": "test"}],
            "artifacts": {"doc": "content"}
        })
        self.assertIn("success", result_save)

        # Load
        result_load = load_plan_tool.invoke({"thread_id": self.test_thread})
        self.assertIn("Plan loaded", result_load)
        self.assertIn("test", result_load)

if __name__ == "__main__":
    unittest.main()