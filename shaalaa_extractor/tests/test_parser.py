import unittest

from shaalaa_extractor.parser import parse_questions


HTML = """
<main>
<div class="section">SECTION - A (40 Marks)</div>
<div class="qbp_item qbp_item_depth_0"><div class="qbp_item_head"><span class="score">[1]</span><span class="qn_number">1.</span><span class="qn_text">Solve x<sup>2</sup> = 4.</span></div></div>
<div class="qbp_item qbp_item_depth_0"><div class="qbp_item_head"><span class="score">[1]</span><span class="qn_number">2. (i)</span></div><div class="qp_result_data"><div class="html_text"><p>Choose the correct option: x<sup>2</sup> = 4.</p></div><div class="html_text"><p>x = 2</p><p>x = -2</p></div><a class="view_solution">VIEW SOLUTION</a></div></div>
<div class="qbp_item qbp_item_depth_0"><div class="qbp_item_head"><span class="score">[1]</span><span class="qn_number">2. (ii)</span><span class="qn_text">Use the table below.<img src="https://example.test/figure.png" alt="geometry"></span><table><tr><th>x</th><th>y</th></tr><tr><td>1</td><td>2</td></tr></table></div></div>
</main>
"""


class ParserTests(unittest.TestCase):
    def test_parser_preserves_questions_and_math_text(self):
        questions = parse_questions(HTML)
        self.assertEqual([q.question_number for q in questions], ["1", "2"])
        self.assertIn("x", questions[0].content[0].value)
        self.assertIn("<sup>2</sup>", questions[0].content[0].metadata["structured_html"])
        self.assertEqual(questions[0].marks, 1)
        self.assertNotIn("VIEW SOLUTION", questions[1].subquestions[0].content[0].value)
        self.assertEqual(questions[1].subquestions[0].content[0].value,
                         "Choose the correct option: x 2 = 4.")

    def test_parser_extracts_subquestions_and_excludes_solution(self):
        question = parse_questions(HTML)[1]
        self.assertEqual([q.question_number for q in question.subquestions], ["i", "ii"])
        self.assertTrue(all("solution" not in str(block.value).lower()
                            for block in question.content))
        self.assertTrue(any(block.type == "image" for block in question.subquestions[1].content))
        self.assertTrue(any(block.type == "table" for block in question.subquestions[1].content))

    def test_parser_keeps_math_structure_and_removes_mcq_options(self):
        question = parse_questions(HTML)[1].subquestions[0]
        self.assertTrue(any(block.type == "math" for block in question.content))
        self.assertNotIn("x = 2", " ".join(str(block.value) for block in question.content))
        self.assertEqual(question.content[1].metadata["structure"], "sup")

    def test_mathjax_structure_is_preserved(self):
        html = HTML.replace(
            "x<sup>2</sup> = 4.",
            "<mjx-container data-semantic-speech-none='x squared' "
            "data-semantic-structure='(1 2)'><mjx-math>x²</mjx-math></mjx-container>",
        )
        question = parse_questions(html)[0]
        math = next(block for block in question.content if block.type == "math")
        self.assertEqual(math.metadata["accessibility"], "x squared")
        self.assertEqual(math.metadata["semantic_structure"], "(1 2)")
        self.assertIn("mjx-container", math.metadata["source_html"])
        self.assertEqual(math.metadata["source_question_number"], "1.")

    def test_intentional_blank_is_a_complete_mcq_stem(self):
        html = HTML.replace(
            "Choose the correct option: x<sup>2</sup> = 4.",
            "The rate of GST is ______.",
        )
        question = parse_questions(html)[1].subquestions[0]
        self.assertIn("______", question.content[0].value)
