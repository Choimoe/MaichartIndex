import unittest
import json
from simai_search.search import RhythmSearcher
from simai_search.db import SimaiDB

class MockDB:
    def get_charts(self, **kwargs):
        return []

class TestRhythmSearcher(unittest.TestCase):
    def setUp(self):
        # Mock DB not needed for _match_pattern test, but needed for instantiation
        # We can bypass logic or use a memory db
        self.searcher = RhythmSearcher(":memory:") 

    def test_match_exact(self):
        # Chart events as Tuples: (time, bpm, is_star, resolution, src_start, src_end)
        chart_events = [
            (0.0, 150, 0, 4.0, 0, 1),
            (1.0, 150, 0, 4.0, 2, 3)
        ]
        # Query events remain Dicts (as parsed from query string)
        query_events = [
            {'time': 0.0, 'bpm': 0, 'is_star': False},
            {'time': 1.0, 'bpm': 0, 'is_star': False}
        ]
        self._normalize(query_events)
        
        result = self.searcher._match_pattern(chart_events, query_events, tolerance=0.01)
        self.assertIsNotNone(result)
        # Expect ((start_idx, end_idx), degree)
        self.assertEqual(result, ((0, 1), 1.0)) 

    def test_match_degree(self):
        # Case 1: Perfect Match
        chart_p = [
            (0.0, 150, 0, 4.0, 0, 0),
            (1.0, 150, 0, 4.0, 0, 0)
        ]
        query = [
            {'time': 0.0, 'bpm': 0, 'is_star': False},
            {'time': 1.0, 'bpm': 0, 'is_star': False}
        ]
        self._normalize(query)
        res_p = self.searcher._match_pattern(chart_p, query, tolerance=0.01)
        self.assertEqual(res_p[1], 1.0)
        
        # Case 2: Partial Match (Interleaved note)
        chart_i = [
            (0.0, 150, 0, 4.0, 0, 0),
            (0.5, 150, 0, 4.0, 0, 0),
            (1.0, 150, 0, 4.0, 0, 0)
        ]
        res_i = self.searcher._match_pattern(chart_i, query, tolerance=0.01)
        self.assertIsNotNone(res_i)
        self.assertAlmostEqual(res_i[1], 2/3, places=2)
        
        # Case 3: Verify Best Match is chosen
        chart_mixed = [
            (0.0, 150, 0, 4.0, 0, 0),
            (0.5, 150, 0, 4.0, 0, 0),
            (1.0, 150, 0, 4.0, 0, 0),
            # Gap
            (3.0, 150, 0, 4.0, 0, 0),
            (4.0, 150, 0, 4.0, 0, 0)
        ]
        res_mixed = self.searcher._match_pattern(chart_mixed, query, tolerance=0.01)
        self.assertEqual(res_mixed[1], 1.0)
        self.assertEqual(res_mixed[0], (3, 4))

    def test_snippet_formatting(self):
        pass

    def test_bpm_filter(self):
        chart_events = [
            (0.0, 150, 0, 4.0, 0, 0),
            (1.0, 150, 0, 4.0, 0, 0)
        ]
        query_events = [{'time': 0.0, 'bpm': 0, 'is_star': False}]
        self._normalize(query_events)
        
        self.assertTrue(self.searcher._match_pattern(chart_events, query_events, 0.01, bpm_min=140, bpm_max=160))
        self.assertFalse(self.searcher._match_pattern(chart_events, query_events, 0.01, bpm_min=160))

    def test_star_filter(self):
        # chart[2] is is_star (0/1)
        chart_events = [
            (0.0, 150, 1, 4.0, 0, 0) # Star
        ]
        
        query_events = [{'time': 0.0, 'bpm': 0, 'is_star': True}]
        self._normalize(query_events)
        self.assertTrue(self.searcher._match_pattern(chart_events, query_events, 0.01))
        
        query_normal = [{'time': 0.0, 'bpm': 0, 'is_star': False}]
        self._normalize(query_normal)
        self.assertTrue(self.searcher._match_pattern(chart_events, query_normal, 0.01))
        
        chart_normal = [(0.0, 150, 0, 4.0, 0, 0)]
        self.assertFalse(self.searcher._match_pattern(chart_normal, query_events, 0.01))

    def _normalize(self, query):
        start = query[0]['time']
        for q in query:
            q['delta'] = q['time'] - start
