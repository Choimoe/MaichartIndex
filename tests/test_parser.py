import unittest
from simai_search.parser import SimaiParser

class TestSimaiParser(unittest.TestCase):
    def setUp(self):
        self.parser = SimaiParser()

    def test_basic_rhythm(self):
        # {4}1,2, -> Note at 0.0, Note at 1.0 (4/4 * 1)
        chart = "{4}1,2,"
        events = self.parser.parse_chart_to_rhythm(chart)
        self.assertEqual(events, [0.0, 1.0])

    def test_simultaneous_notes(self):
        # {4}1/2,3, -> Note at 0.0, Note at 1.0
        # parse_chart_to_rhythm flattens simultaneous notes to a single timestamp event
        chart = "{4}1/2,3,"
        events = self.parser.parse_chart_to_rhythm(chart)
        self.assertEqual(events, [0.0, 1.0])

    def test_rest(self):
        # {4}1,,2, -> Note at 0.0, Blank at 1.0, Note at 2.0
        chart = "{4}1,,2,"
        events = self.parser.parse_chart_to_rhythm(chart)
        self.assertEqual(events, [0.0, 2.0])

    def test_resolution_change(self):
        # {4}1,{8}1,1, -> 0.0, 1.0 (change to 8th), 1.0+0.5=1.5
        chart = "{4}1,{8}1,1,"
        events = self.parser.parse_chart_to_rhythm(chart)
        self.assertEqual(events, [0.0, 1.0, 1.5])

    def test_messy_chart(self):
        # Comments, spaces, newlines
        chart = """
        {4} 1, // comment
        2h[1:1],
        E
        """
        events = self.parser.parse_chart_to_rhythm(chart)
        self.assertEqual(events, [0.0, 1.0])

    def test_parse_maidata_structure(self):
        content = """
&title=TestSong
&inote_4=
{4}1,2,
&inote_5=
{4}1,2,3,4,
"""
        parsed = self.parser.parse_maidata(content)
        self.assertEqual(parsed['metadata']['title'], 'TestSong')
        self.assertIn(4, parsed['charts'])
        self.assertIn(5, parsed['charts'])
