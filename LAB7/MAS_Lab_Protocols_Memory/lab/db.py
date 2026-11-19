"""Готовое хранилище: факты о мире, предпочтения и снимки задач."""
import json
import sqlite3
import uuid
from pathlib import Path

ROOMS = [
    {"id": "A-101", "building": "A", "capacity": 24, "projector": True},
    {"id": "A-102", "building": "A", "capacity": 30, "projector": True},
    {"id": "B-201", "building": "B", "capacity": 24, "projector": True},
    {"id": "B-202", "building": "B", "capacity": 40, "projector": True},
    {"id": "A-103", "building": "A", "capacity": 12, "projector": False},
]


class WorldStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, data TEXT);
                CREATE TABLE IF NOT EXISTS checkpoints (key TEXT PRIMARY KEY, data TEXT);
                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY, room_id TEXT, date TEXT, time TEXT,
                    user_id TEXT, task_id TEXT, UNIQUE(room_id,date,time));
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def search_rooms(self, requirements):
        with self.connect() as db:
            busy = {r[0] for r in db.execute(
                'SELECT room_id FROM reservations WHERE date=? AND time=?',
                (requirements['date'], requirements['time']))}
        return [dict(room) for room in ROOMS if room['id'] not in busy
                and room['capacity'] >= requirements['people']
                and (not requirements.get('projector') or room['projector'])
                and (not requirements.get('building') or room['building'] == requirements['building'])]

    def reserve_room(self, user_id, task_id, room_id, requirements):
        reservation = {"id": str(uuid.uuid4()), "room_id": room_id,
                       "date": requirements['date'], "time": requirements['time'], "user_id": user_id}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            suitable = any(room['id'] == room_id for room in self.search_rooms(requirements))
            if not suitable:
                return {"ok": False, "reason": "occupied"}
            try:
                db.execute('INSERT INTO reservations VALUES (?,?,?,?,?,?)',
                           (*reservation.values(), task_id))
            except sqlite3.IntegrityError:
                return {"ok": False, "reason": "occupied"}
        return {"ok": True, "reservation": reservation}

    def read_profile(self, user_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM profiles WHERE user_id=?', (user_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def write_profile(self, user_id, profile):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO profiles VALUES (?,?)',
                       (user_id, json.dumps(profile, ensure_ascii=False)))
        return profile

    def save_checkpoint(self, key, data):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO checkpoints VALUES (?,?)',
                       (key, json.dumps(data, ensure_ascii=False)))

    def load_checkpoint(self, key):
        with self.connect() as db:
            row = db.execute('SELECT data FROM checkpoints WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def occupy(self, room_id, date, time):
        with self.connect() as db:
            db.execute('INSERT INTO reservations VALUES (?,?,?,?,?,?)',
                       (str(uuid.uuid4()), room_id, date, time, 'external', 'external'))

    def reservations(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute('SELECT * FROM reservations')]
