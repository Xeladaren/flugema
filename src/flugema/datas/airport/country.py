import csv
import datetime
import http.client
import io
import os.path
import sqlite3
import urllib

from functools import lru_cache

from .ourairports import OurAirports

import logging
logger = logging.getLogger(__name__)

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")

continent = {
    "AF": "Africa",
    "AN": "Antarctica",
    "AS": "Asia",
    "EU": "Europe",
    "NA": "North America",
    "OC": "Oceania",
    "SA": "South America"
}

class Country():

    @classmethod
    def update(cls):

        reader = OurAirports.countries()

        if reader:

            database = sqlite3.connect(DATABASE_PATH)
            cursor = database.cursor()
            cursor.execute("DROP TABLE IF EXISTS countries;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS countries (
                    id INTEGER PRIMARY KEY,
                    code TEXT,
                    name TEXT,
                    continent TEXT,
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
                    INSERT INTO countries (
                        id, code, name, continent, wikipedia_link, keywords
                    ) VALUES (
                        :id, :code, :name, :continent, :wikipedia_link, :keywords
                    );
                """, row)

            database.commit()
            database.close()
            logger.info("Countries updated !")

    @classmethod
    @lru_cache(maxsize=None)
    def from_iso_code(cls, code: str):

        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()
        cursor.execute("SELECT * FROM countries WHERE code = ?", (code,))

        for row in cursor.fetchall():
            return Country(dict(row))

        database.close()

        return None

    def __init__(self, data):
        self.data = data

    def __eq__(self, other):
        if type(other) == str:
            return self.data["code"] == other
        elif type(other) == Country:
            return self.data["code"] == other.data["code"]

    def __str__(self):
        return f"Country({self.data["name"]})"

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self.data["name"]

    @property
    def continent(self):
        return continent[self.data["continent"]]