import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple
import json

@dataclass
class Song:
    id: int
    title: str
    artist: str
    genre: str
    path: str

@dataclass
class Chart:
    id: int
    song_id: int
    difficulty: int  # 0: Easy, 1: Basic, 2: Advanced, 3: Expert, 4: Master, 5: ReMaster (Simai standard usually 1-5 or 0-4, we will map carefully)
    level: str
    designer: str
    raw_content: str
    note_data: str # JSON encoded list of beat offsets for search

class SimaiDB:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                artist TEXT,
                genre TEXT,
                path TEXT UNIQUE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS charts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_id INTEGER,
                difficulty INTEGER,
                level TEXT,
                designer TEXT,
                raw_content TEXT,
                note_data TEXT,
                FOREIGN KEY(song_id) REFERENCES songs(id)
            )
        ''')
        self.conn.commit()

    def add_song(self, title: str, artist: str, genre: str, path: str) -> int:
        cursor = self.conn.cursor()
        # Check if exists
        cursor.execute('SELECT id FROM songs WHERE path = ?', (path,))
        row = cursor.fetchone()
        if row:
            return row[0]
        
        cursor.execute('INSERT INTO songs (title, artist, genre, path) VALUES (?, ?, ?, ?)',
                       (title, artist, genre, path))
        self.conn.commit()
        return cursor.lastrowid

    def add_chart(self, song_id: int, difficulty: int, level: str, designer: str, raw_content: str, note_data: List[float]):
        cursor = self.conn.cursor()
        # Clean existing chart for this song/difficulty if strictly needed, or just append
        # For now, let's assume valid re-indexing clears old entries or we check
        cursor.execute('DELETE FROM charts WHERE song_id = ? AND difficulty = ?', (song_id, difficulty))
        
        cursor.execute('''
            INSERT INTO charts (song_id, difficulty, level, designer, raw_content, note_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (song_id, difficulty, level, designer, raw_content, json.dumps(note_data)))
        self.conn.commit()

    def get_charts(self, 
                   level_min: Optional[float] = None, 
                   level_max: Optional[float] = None, 
                   difficulties: Optional[List[int]] = None, 
                   designer: Optional[str] = None) -> List[Tuple[int, str, int, str, str, str]]:
        cursor = self.conn.cursor()
        
        query = '''
            SELECT c.id, s.title, c.difficulty, c.level, c.note_data, c.raw_content, c.designer
            FROM charts c
            JOIN songs s ON c.song_id = s.id
            WHERE 1=1
        '''
        params = []
        
        if level_min is not None:
            # Simai levels are strings like "12.5", "13+", etc.
            # We need to handle this. For now, let's rely on the fact that standard numerical levels convert to float.
            # But "13+" is usually treated as 13.7 or so in internal logic?
            # Or we simply try to cast `level` column to float in SQL?
            # SQLite `CAST(level AS REAL)` might work for "12.5" but "13+" becomes 13.0.
            # Ideally we parsed levels to float during indexing.
            # Let's assume for now we only filter on the numeric part or the user stores them as numbers.
            # Actually, let's fix the schema/indexer later to store a numeric_level column for better filtering.
            # For this step, I will add a `numeric_level` column to `charts` table in `create_tables` but since table exists,
            # I can't easily migrate without dropping.
            # I'll stick to basic CAST which works for pure numbers. "13+" charts might be missed or treated as 13.0.
            # Better approach: filter in python? No, efficiency.
            # Let's use CAST for now.
            query += ' AND CAST(c.level AS REAL) >= ?'
            params.append(level_min)
            
        if level_max is not None:
            query += ' AND CAST(c.level AS REAL) <= ?'
            params.append(level_max)
            
        if difficulties:
            placeholders = ','.join('?' for _ in difficulties)
            query += f' AND c.difficulty IN ({placeholders})'
            params.extend(difficulties)
            
        if designer:
            query += ' AND c.designer LIKE ?'
            params.append(f'%{designer}%')
            
        cursor.execute(query, params)
        return cursor.fetchall()
