import os
import sys
from .parser import SimaiParser
from .db import SimaiDB

class Indexer:
    def __init__(self, db_path: str, data_root: str):
        self.db = SimaiDB(db_path)
        self.data_root = data_root
        self.parser = SimaiParser()

    def run(self):
        print(f"Scanning {self.data_root}...")
        count = 0
        for root, dirs, files in os.walk(self.data_root):
            for file in files:
                if file.lower() == 'maidata.txt':
                    full_path = os.path.join(root, file)
                    try:
                        self.process_file(full_path)
                        count += 1
                        if count % 10 == 0:
                            print(f"Processed {count} files...")
                    except Exception as e:
                        print(f"Error processing {full_path}: {e}")
        print(f"Done! Processed {count} files.")

    def process_file(self, full_path: str):
        # Read file with fallback encoding
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(full_path, 'r', encoding='cp932') as f:
                content = f.read()
                
        parsed = self.parser.parse_maidata(content)
        metadata = parsed.get('metadata', {})
        charts = parsed.get('charts', {})
        
        # Insert Song
        title = metadata.get('title', 'Unknown')
        artist = metadata.get('artist', 'Unknown')
        genre = metadata.get('genre', 'Unknown')
        
        # Create song in DB
        song_id = self.db.add_song(title, artist, genre, full_path)
        
        # Insert Charts
        for difficulty, chart_text in charts.items():
            # difficulty is 1-indexed (1=Easy, ..., 5=Master, 6=ReMaster)
            # We store as is
            level_key = f'lv_{difficulty}'
            level = metadata.get(level_key, '')
            designer_key = f'des_{difficulty}'
            designer = metadata.get(designer_key, '')
            
            # Parse rhythm
            note_data = self.parser.parse_chart_to_rhythm(chart_text)
            
            self.db.add_chart(song_id, difficulty, level, designer, chart_text, note_data)

if __name__ == "__main__":
    # Test run
    indexer = Indexer("maichart.db", "data/Maichart-Converts")
    indexer.run()
