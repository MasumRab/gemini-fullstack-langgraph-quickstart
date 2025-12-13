import unittest
from agent.memory_tools import save_plan_tool, load_plan_tool
from agent.persistence import PLAN_DIR
import os
import shutil

class TestMemoryTools(unittest.TestCase):
    def setUp(self):
        os.makedirs(PLAN_DIR, exist_ok=True)
        self.test_thread = "test_tool_thread"

    def tearDown(self):
        # Cleanup
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
