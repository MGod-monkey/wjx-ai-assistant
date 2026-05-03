import unittest

from wjx_assistant.ai_client import parse_ai_json_response
from wjx_assistant.answers import option_letter_to_index, validate_answers
from wjx_assistant.config import normalize_config
from wjx_assistant.schema import Option, Question


class ConfigTests(unittest.TestCase):
    def test_normalize_config_swaps_wait_bounds(self):
        cfg = normalize_config({"wait_min": 20, "wait_max": 5, "browser_width": 100})
        self.assertEqual(cfg.wait_min, 5)
        self.assertEqual(cfg.wait_max, 20)
        self.assertEqual(cfg.browser_width, 320)


class AiParsingTests(unittest.TestCase):
    def test_parse_json_from_markdown_block(self):
        parsed = parse_ai_json_response('```json\n{"1":"A","2":["B","C"]}\n```')
        self.assertEqual(parsed["1"], "A")
        self.assertEqual(parsed["2"], ["B", "C"])

    def test_parse_simple_pairs_fallback(self):
        parsed = parse_ai_json_response('1: A\n2: B')
        self.assertEqual(parsed["1"], "A")
        self.assertEqual(parsed["2"], "B")


class AnswerTests(unittest.TestCase):
    def test_option_letter_to_index(self):
        self.assertEqual(option_letter_to_index("A"), 1)
        self.assertEqual(option_letter_to_index("c"), 3)
        self.assertEqual(option_letter_to_index("2"), 2)

    def test_validate_answers_clamps_choice(self):
        questions = [Question(id="1", raw_type="3", title="x", options=[Option("a"), Option("b")])]
        answers = validate_answers(questions, {"1": "Z"})
        self.assertEqual(answers["1"], "B")

    def test_validate_answers_adds_default(self):
        questions = [Question(id="1", raw_type="1", title="x")]
        answers = validate_answers(questions, {})
        self.assertEqual(answers["1"], "满意")


if __name__ == "__main__":
    unittest.main()