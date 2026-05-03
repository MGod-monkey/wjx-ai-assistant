import unittest

from wjx_assistant.ai_client import _format_api_error, parse_ai_json_response
from wjx_assistant.answers import option_letter_to_index, validate_answers
from wjx_assistant.config import normalize_config
from wjx_assistant.filler import _split_answer
from wjx_assistant.parser import _clean_question_text, _element_text, _extract_choice_options
from wjx_assistant.schema import Option, Question


class ConfigTests(unittest.TestCase):
    def test_normalize_config_swaps_wait_bounds(self):
        cfg = normalize_config({"wait_min": 20, "wait_max": 5, "browser_width": 100})
        self.assertEqual(cfg.wait_min, 5)
        self.assertEqual(cfg.wait_max, 20)
        self.assertEqual(cfg.browser_width, 320)

    def test_normalize_config_accepts_fallback_string(self):
        cfg = normalize_config({"model_fallbacks": "A,B"})
        self.assertEqual(cfg.model_fallbacks, ["A", "B"])


class AiParsingTests(unittest.TestCase):
    def test_parse_json_from_markdown_block(self):
        parsed = parse_ai_json_response('```json\n{"1":"A","2":["B","C"]}\n```')
        self.assertEqual(parsed["1"], "A")
        self.assertEqual(parsed["2"], ["B", "C"])

    def test_parse_simple_pairs_fallback(self):
        parsed = parse_ai_json_response('1: A\n2: B')
        self.assertEqual(parsed["1"], "A")
        self.assertEqual(parsed["2"], "B")

    def test_model_disabled_error_is_actionable(self):
        class Response:
            status_code = 403
            text = '{"code":30003,"message":"Model disabled."}'

            def json(self):
                return {"code": 30003, "message": "Model disabled."}

        message = _format_api_error(Response(), "deepseek-ai/DeepSeek-V2.5")
        self.assertIn("模型已被禁用", message)
        self.assertIn("deepseek-ai/DeepSeek-V3", message)


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


class FakeElement:
    def __init__(self, text="", attrs=None, children=None):
        self.text = text
        self.attrs = attrs or {}
        self.children = children or {}

    def get_attribute(self, name):
        return self.attrs.get(name, "")

    def find_elements(self, by, selector):
        return self.children.get(selector, [])


class ParserHelperTests(unittest.TestCase):
    def test_hidden_element_text_uses_text_content(self):
        elem = FakeElement(text="", attrs={"textContent": "  您的性别:  "})
        self.assertEqual(_element_text(elem), "您的性别:")

    def test_clean_question_text_removes_number_and_tip(self):
        text = _clean_question_text("* 5. 您刷到过哪些类型?【请选择1-10项,已选择0项】")
        self.assertEqual(text, "您刷到过哪些类型?")

    def test_extract_choice_options_uses_label_text_content(self):
        div = FakeElement(children={
            ".ui-controlgroup .label": [
                FakeElement(attrs={"textContent": "A.男"}),
                FakeElement(attrs={"textContent": "B.女"}),
            ]
        })
        labels = [option.label for option in _extract_choice_options(div)]
        self.assertEqual(labels, ["男", "女"])


class FillerHelperTests(unittest.TestCase):
    def test_split_answer_handles_chinese_comma(self):
        self.assertEqual(_split_answer("A，C, D"), ["A", "C", "D"])

    def test_split_answer_handles_list(self):
        self.assertEqual(_split_answer(["A", "", "B"]), ["A", "B"])


if __name__ == "__main__":
    unittest.main()