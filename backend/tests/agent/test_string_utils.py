import unittest
from agent.string_utils import join_and_truncate

class TestJoinAndTruncate(unittest.TestCase):
    def test_basic_join(self):
        strings = ["hello", "world"]
        result = join_and_truncate(strings, separator=" ", max_length=100)
        self.assertEqual(result, "hello world")

    def test_truncate_exact(self):
        strings = ["hello", "world"]
        # "hello world" is 11 chars
        result = join_and_truncate(strings, separator=" ", max_length=11)
        self.assertEqual(result, "hello world")

    def test_truncate_partial(self):
        strings = ["hello", "world"]
        # Limit 8: "hello wo"
        result = join_and_truncate(strings, separator=" ", max_length=8)
        self.assertEqual(result, "hello wo")

    def test_truncate_first_string(self):
        strings = ["hello world"]
        result = join_and_truncate(strings, separator=" ", max_length=5)
        self.assertEqual(result, "hello")

    def test_many_strings(self):
        strings = ["a"] * 10
        # "a a a ..."
        # 10 chars + 9 spaces = 19
        result = join_and_truncate(strings, separator=" ", max_length=5)
        self.assertEqual(result, "a a a")

    def test_empty_list(self):
        result = join_and_truncate([], max_length=10)
        self.assertEqual(result, "")

    def test_separator_overhead(self):
        strings = ["a", "b"]
        # "a--b" length 4
        # limit 3 -> "a" (can't fit "--b")
        result = join_and_truncate(strings, separator="--", max_length=3)
        self.assertEqual(result, "a")

if __name__ == "__main__":
    unittest.main()
