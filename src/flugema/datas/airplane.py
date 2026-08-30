
import os
import sqlite3
import datetime

from functools import lru_cache

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")

class Airplane():

    @classmethod
    def create_database(cls):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS airplanes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration TEXT NOT NULL UNIQUE,
                type_code TEXT NOT NULL,
                name TEXT,
                manufacturer TEXT,
                engine_type TEXT,
                engine_count INTEGER,
                wtc TEXT,
                description TEXT
            );
        """)

        database.commit()
        database.close()

    @classmethod
    @lru_cache(maxsize=None)
    def from_id(cls, id: int):
        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()

        cursor.execute("SELECT * FROM airplanes WHERE id = ?", (id,))
        result = cursor.fetchone()

        database.commit()
        database.close()

        if result:
            return Airplane(dict(result))
        else:
            return None

    @classmethod
    def from_reg(cls, registration: str):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("SELECT id FROM airplanes WHERE registration = ?", (registration,))
        result = cursor.fetchone()

        database.commit()
        database.close()

        if result:
            return Airplane.from_id(result[0])
        else:
            return None

    @classmethod
    def all(cls) -> list[Airplane]:
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("SELECT id FROM airplanes")
        results = cursor.fetchall()

        all_planes = []
        for result in results:
            all_planes.append(Airplane.from_id(result[0]))

        database.commit()
        database.close()

        return all_planes

    @classmethod
    def new(cls, registration: str, type_code: str) -> Airplane:
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            INSERT INTO airplanes (registration, type_code)
            VALUES (?, ?)
        """, (registration, type_code))
        new_id = cursor.lastrowid

        database.commit()
        database.close()

        return Airplane.from_id(new_id)

    def __init__(self, data):
        self.data = data

    def __str__(self):
        return f"{self.registration} - {self.type}"

    def __repr__(self):
        return f"Airplane(id={self.id}, reg={self.registration}, type={self.type})"

    @property
    def id(self):
        return self.data['id']

    @property
    def registration(self):
        return self.data['registration']

    @property
    def type(self):
        return self.data['type_code']