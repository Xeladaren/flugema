import csv
import datetime
import http.client
import io
import os.path
import sqlite3
import urllib

from functools import lru_cache

from .country import continent
from .ourairports import OurAirports

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")

class Region():

    @classmethod
    def update(cls):

        reader = OurAirports.regions()
        if reader:
            
            database = sqlite3.connect(DATABASE_PATH)
            cursor = database.cursor()
            cursor.execute("DROP TABLE IF EXISTS regions;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS regions (
                    id INTEGER PRIMARY KEY,
                    code TEXT,
                    local_code TEXT,
                    name TEXT,
                    continent TEXT,
                    iso_country TEXT,
                    wikipedia_link TEXT,
                    keywords TEXT
                );
            """)

            for row in reader:

                for elem in row:
                    if row[elem] == "":
                        row[elem] = None

                row['id'] = int(row['id'])

                cursor.execute("""
                    INSERT INTO regions (
                        id, code, local_code, name, continent, iso_country, wikipedia_link, keywords
                    ) VALUES (
                        :id, :code, :local_code, :name, :continent, :iso_country, :wikipedia_link, :keywords
                    );
                """, row)

            database.commit()
            database.close()
            print("Regions updated !")

    @classmethod
    @lru_cache(maxsize=None)
    def from_iso_code(cls, code: str):

        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()
        cursor.execute("SELECT * FROM regions WHERE code = ?", (code,))

        for row in cursor.fetchall():
            return Region(dict(row))

        database.close()

        return None

    def __init__(self, data):
        self.data = data

    def __eq__(self, other):
        if type(other) == str:
            return self.data["code"] == other
        elif type(other) == Region:
            return self.data["code"] == other.data["code"]

    def __str__(self):
        return f"Region({self.data["name"]})"

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self.data["name"]

    @property
    def continent(self):
        return continent[self.data["continent"]]
