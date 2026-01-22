import sqlite3
from dataclasses import dataclass
from typing import List, Optional
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

    def get_all_charts(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.id, s.title, c.difficulty, c.level, c.note_data, c.raw_content
            FROM charts c
            JOIN songs s ON c.song_id = s.id
        ''')
        return cursor.fetchall()
