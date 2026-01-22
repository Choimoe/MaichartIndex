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
        chart_events = [0.0, 1.0, 2.0, 3.0]
        query_deltas = [0.0, 1.0] # Matches 0-1, 1-2, 2-3
        
        self.assertTrue(self.searcher._match_pattern(chart_events, query_deltas, tolerance=0.01))

    def test_match_gap(self):
        # Chart: Note, Rest, Note (0.0, 2.0)
        # Query: Note, Rest, Note (Deltas: 0.0, 2.0)
        chart_events = [0.0, 2.0, 3.0]
        query_deltas = [0.0, 2.0]
        
        self.assertTrue(self.searcher._match_pattern(chart_events, query_deltas, tolerance=0.01))

    def test_no_match(self):
        chart_events = [0.0, 1.0, 2.0]
        query_deltas = [0.0, 0.5] # 8th note pattern
        
        self.assertFalse(self.searcher._match_pattern(chart_events, query_deltas, tolerance=0.01))

    def test_tolerance(self):
        chart_events = [0.0, 1.005]
        query_deltas = [0.0, 1.0]
        
        # Within 0.01 tolerance
        self.assertTrue(self.searcher._match_pattern(chart_events, query_deltas, tolerance=0.01))
        
        # Out of tolerance (strict)
        self.assertFalse(self.searcher._match_pattern(chart_events, query_deltas, tolerance=0.001))
