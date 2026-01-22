import unittest
from simai_search.parser import SimaiParser

class TestSimaiParser(unittest.TestCase):
    def setUp(self):
        self.parser = SimaiParser()

    def test_basic_rhythm(self):
        # {4}1,2, -> Note at 0.0, Note at 1.0
        chart = "{4}1,2,"
        events = self.parser.parse_chart_to_rhythm(chart)
        # Check times
        times = [e['time'] for e in events]
        self.assertEqual(times, [0.0, 1.0])
        self.assertEqual(events[0]['is_star'], False)
        # {4}1,2,
        # Index logic:
        # 0123456
        # {4}1,2,
        # Event 1: '1' at index 3. Comma at 4.
        # src_start=3, src_end=5?
        # In parser logic:
        # commas (char 4) -> events.append(..., src_start=0, src_end=5)
        # Because step_start_idx was 0 initially.
        # Then step_start_idx becomes 5.
        # Event 2: '2' at index 5. Comma at 6.
        # Comma (char 6) -> events.append(..., src_start=5, src_end=7)
        self.assertEqual(events[0]['src_start'], 0)
        self.assertEqual(events[0]['src_end'], 5)


    def test_star_detection(self):
        # 1-4[4:1] is a slide (star)
        chart = "{4}1-4[4:1],"
        events = self.parser.parse_chart_to_rhythm(chart)
        self.assertEqual(events[0]['is_star'], True)
        
        # 1$ is a star tap
        chart = "{4}1$,"
        events = self.parser.parse_chart_to_rhythm(chart)
        self.assertEqual(events[0]['is_star'], True)

    def test_bpm_tracking(self):
        # (150){4}1,(300)1,
        chart = "(150){4}1,(300)1,"
        events = self.parser.parse_chart_to_rhythm(chart, initial_bpm=100)
        
        # Event 1 at 0.0: BPM should be 150 (set before note)
        self.assertEqual(events[0]['bpm'], 150)
        
        # Event 2 at 1.0: BPM should be 300
        self.assertEqual(events[1]['bpm'], 300)

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
