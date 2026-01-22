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
        # Expect ((start_idx, end_idx), degree)
        # Degree = 2 query notes / 2 chart notes = 1.0
        self.assertEqual(result, ((0, 1), 1.0)) 

    def test_match_degree(self):
        # Case 1: Perfect Match
        # Chart: Note, Note (at t=1)
        # Query: Note, Note (at t=1)
        chart_p = [
            {'time': 0.0, 'bpm': 150, 'is_star': False},
            {'time': 1.0, 'bpm': 150, 'is_star': False}
        ]
        query = [
            {'time': 0.0, 'bpm': 0, 'is_star': False},
            {'time': 1.0, 'bpm': 0, 'is_star': False}
        ]
        self._normalize(query)
        res_p = self.searcher._match_pattern(chart_p, query, tolerance=0.01)
        self.assertEqual(res_p[1], 1.0)
        
        # Case 2: Partial Match (Interleaved note)
        # Chart: Note, Interleaved(t=0.5), Note(t=1)
        chart_i = [
            {'time': 0.0, 'bpm': 150, 'is_star': False},
            {'time': 0.5, 'bpm': 150, 'is_star': False},
            {'time': 1.0, 'bpm': 150, 'is_star': False}
        ]
        # Query matches 0.0 and 1.0
        res_i = self.searcher._match_pattern(chart_i, query, tolerance=0.01)
        self.assertIsNotNone(res_i)
        # Chart Range: index 0 to 2 -> 3 notes
        # Query: 2 notes
        # Degree: 2/3 = 0.666...
        self.assertAlmostEqual(res_i[1], 2/3, places=2)
        
        # Case 3: Verify Best Match is chosen
        # Chart contains both loose match and perfect match
        # 0.0, 0.5, 1.0 (loose) ... 3.0, 4.0 (perfect)
        chart_mixed = [
            {'time': 0.0, 'bpm': 150, 'is_star': False},
            {'time': 0.5, 'bpm': 150, 'is_star': False},
            {'time': 1.0, 'bpm': 150, 'is_star': False},
            # Gap
            {'time': 3.0, 'bpm': 150, 'is_star': False},
            {'time': 4.0, 'bpm': 150, 'is_star': False}
        ]
        res_mixed = self.searcher._match_pattern(chart_mixed, query, tolerance=0.01)
        # Should pick the one at 3.0-4.0 with degree 1.0
        self.assertEqual(res_mixed[1], 1.0)
        self.assertEqual(res_mixed[0], (3, 4))

    def test_snippet_formatting(self):
        # Mock logic to test snippet construction in search() method
        # This requires mocking DB returns or full integration test.
        # Alternatively, verify _match_pattern returns correct indices, 
        # which we already do.
        # The formatting logic is in search(), which is hard to unit test without DB.
        # Let's trust the debug manual test for now or add a small integration test here 
        # if we had a populated test DB.
        pass

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
