import unittest

from lantern_orch.intent import classify


class TrickVoiceTests(unittest.TestCase):
    def test_common_tricks_map_to_dim_os_names(self):
        self.assertEqual(classify("please dance for me").command_name, "Dance1")
        self.assertEqual(classify("do a front flip").command_name, "FrontFlip")
        self.assertEqual(classify("can you wave").command_name, "Hello")
        self.assertEqual(classify("lie down").command_name, "StandDown")

    def test_ambiguous_text_is_ignored(self):
        self.assertIsNone(classify("what tricks can you do"))


if __name__ == "__main__":
    unittest.main()
