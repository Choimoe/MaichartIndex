import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple
import json
import zlib

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
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
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
                raw_content BLOB,
                note_data BLOB,
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
        
        # Compress large text fields
        raw_content_blob = zlib.compress(raw_content.encode('utf-8'))
        note_data_blob = zlib.compress(json.dumps(note_data).encode('utf-8'))
        
        cursor.execute('''
            INSERT INTO charts (song_id, difficulty, level, designer, raw_content, note_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (song_id, difficulty, level, designer, raw_content_blob, note_data_blob))
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
        rows = cursor.fetchall()
        
        decoded_rows = []
        for row in rows:
            # Row: id, title, diff, level, note_data(blob), raw_content(blob), designer
            c_id, title, diff, level, note_blob, raw_blob, desg = row
            
            # Decompress
            try:
                # If it's already bytes, assume compressed. If string, legacy db? 
                # We enforce rebuild, so always bytes.
                if isinstance(note_blob, bytes):
                    note_json = zlib.decompress(note_blob).decode('utf-8')
                else:
                    note_json = note_blob # Fallback if someone didn't rebuild
                
                if isinstance(raw_blob, bytes):
                    raw_content = zlib.decompress(raw_blob).decode('utf-8')
                else:
                    raw_content = raw_blob
            except Exception as e:
                print(f"Error decompressing chart {c_id}: {e}")
                continue
                
            decoded_rows.append((c_id, title, diff, level, note_json, raw_content, desg))
            
        return decoded_rows
