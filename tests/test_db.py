import unittest
import json
from simai_search.db import SimaiDB

class TestSimaiDB(unittest.TestCase):
    def setUp(self):
        self.db = SimaiDB(":memory:")

    def test_add_and_get_song(self):
        song_id = self.db.add_song("Title", "Artist", "Genre", "/path/to/file")
        self.assertIsNotNone(song_id)
        
        # Verify deduplication
        song_id_2 = self.db.add_song("Title", "Artist", "Genre", "/path/to/file")
        self.assertEqual(song_id, song_id_2)

    def test_add_and_filter_charts(self):
        song_id = self.db.add_song("Title", "Artist", "Genre", "/path")
        self.db.add_chart(song_id, 4, "13", "Designer", "Content", [0.0, 1.0])
        self.db.add_chart(song_id, 5, "14.5", "Designer2", "Content", [0.0, 1.0])
        
        # Test Filter by difficulty
        charts = self.db.get_charts(difficulties=[4])
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0][2], 4)
        
        # Test Filter by level
        charts = self.db.get_charts(level_min=14.0)
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0][2], 5)

    def test_designer_search(self):
        song_id = self.db.add_song("A", "B", "C", "D")
        self.db.add_chart(song_id, 1, "1", "Alice", "C", [])
        self.db.add_chart(song_id, 2, "1", "Bob", "C", [])
        
        charts = self.db.get_charts(designer="Ali")
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0][6], "Alice")
