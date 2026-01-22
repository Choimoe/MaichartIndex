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
        # Chart events
        chart_events = [
            {'time': 0.0, 'bpm': 150, 'is_star': False, 'src_start': 0, 'src_end': 1},
            {'time': 1.0, 'bpm': 150, 'is_star': False, 'src_start': 2, 'src_end': 3}
        ]
        # Query events
        query_events = [
            {'time': 0.0, 'bpm': 0, 'is_star': False},
            {'time': 1.0, 'bpm': 0, 'is_star': False}
        ]
        self._normalize(query_events)
        
        result = self.searcher._match_pattern(chart_events, query_events, tolerance=0.01)
        self.assertIsNotNone(result)
        self.assertEqual(result, (0, 1)) # Start idx 0, End idx 1

    def test_bpm_filter(self):
        chart_events = [
            {'time': 0.0, 'bpm': 150, 'is_star': False},
            {'time': 1.0, 'bpm': 150, 'is_star': False}
        ]
        query_events = [{'time': 0.0, 'bpm': 0, 'is_star': False}]
        self._normalize(query_events)
        
        # Match matches logic
        self.assertTrue(self.searcher._match_pattern(chart_events, query_events, 0.01, bpm_min=140, bpm_max=160))
        self.assertFalse(self.searcher._match_pattern(chart_events, query_events, 0.01, bpm_min=160))

    def test_star_filter(self):
        chart_events = [
            {'time': 0.0, 'bpm': 150, 'is_star': True} # Star
        ]
        
        # Query requiring star
        query_events = [{'time': 0.0, 'bpm': 0, 'is_star': True}]
        self._normalize(query_events)
        self.assertTrue(self.searcher._match_pattern(chart_events, query_events, 0.01))
        
        # Query normal note (should match star if normal query implies "any"?)
        # Current logic: query normal (is_star=False) matches anything.
        query_normal = [{'time': 0.0, 'bpm': 0, 'is_star': False}]
        self._normalize(query_normal)
        self.assertTrue(self.searcher._match_pattern(chart_events, query_normal, 0.01))
        
        # Chart normal, Query Star -> Fail
        chart_normal = [{'time': 0.0, 'bpm': 150, 'is_star': False}]
        self.assertFalse(self.searcher._match_pattern(chart_normal, query_events, 0.01))

    def _normalize(self, query):
        start = query[0]['time']
        for q in query:
            q['delta'] = q['time'] - start
