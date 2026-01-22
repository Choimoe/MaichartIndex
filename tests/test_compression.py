import unittest
import sqlite3
import zlib
import json
from simai_search.db import SimaiDB

class TestDBCompression(unittest.TestCase):
    def setUp(self):
        self.db = SimaiDB(":memory:")

    def test_compression_cycle(self):
        """Test that data is compressed in DB and decompressed on retrieval."""
        song_id = self.db.add_song("Title", "Artist", "Genre", "/path")
        
        original_content = "This is a very long string used to test zlib compression." * 10
        original_notes = [1.0, 2.0, 3.0, 4.0] * 10
        
        # 1. Add Chart (Should compress)
        self.db.add_chart(
            song_id=song_id,
            difficulty=4,
            level="13",
            designer="Designer",
            raw_content=original_content,
            note_data=original_notes
        )
        
        # 2. Verify compression in raw DB
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT raw_content, note_data FROM charts WHERE id=1")
        raw_row = cursor.fetchone()
        
        raw_blob = raw_row[0]
        note_blob = raw_row[1]
        
        # Assert stored type is bytes (BLOB)
        self.assertIsInstance(raw_blob, bytes)
        self.assertIsInstance(note_blob, bytes)
        
        # Assert content is actually compressed
        # Zlib header usually starts with x78 (120) for default compression
        # But definitively it should NOT be equal to original string encoded
        self.assertNotEqual(raw_blob, original_content.encode('utf-8'))
        
        # Verify we can manually decompress
        decompressed_content = zlib.decompress(raw_blob).decode('utf-8')
        self.assertEqual(decompressed_content, original_content)
        
        # 3. Verify transparent decompression via get_charts
        charts = self.db.get_charts(difficulties=[4])
        self.assertEqual(len(charts), 1)
        
        # charts[0] = (id, title, diff, level, note_data_json, raw_content, designer)
        retrieved_notes_json = charts[0][4]
        retrieved_content = charts[0][5]
        
        self.assertIsInstance(retrieved_content, str)
        self.assertEqual(retrieved_content, original_content)
        
        self.assertIsInstance(retrieved_notes_json, str)
        self.assertEqual(json.loads(retrieved_notes_json), original_notes)

if __name__ == '__main__':
    unittest.main()
