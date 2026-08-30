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

class Frequency():

    @classmethod
    def update(cls):

        reader = OurAirports.frequencies()
        if reader:
            database = sqlite3.connect(DATABASE_PATH)
            cursor = database.cursor()

            cursor.execute("DROP TABLE IF EXISTS frequencies;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS frequencies (
                    id INTEGER PRIMARY KEY,
                    airport INTEGER NOT NULL,
                    type TEXT,
                    description TEXT,
                    frequency_mhz REAL,

                    FOREIGN KEY (airport) REFERENCES airports(id)
                );
            """)

            for row in reader:

                for elem in row:
                    if row[elem] == "":
                        row[elem] = None

                row['id'] = int(row['id'])
                row['airport'] = int(row['airport_ref'])
                row['frequency_mhz'] = float(row['frequency_mhz'])

                del row['airport_ref']
                del row['airport_ident']

                cursor.execute("""
                    INSERT INTO frequencies (
                        id, airport, type, description, frequency_mhz
                    ) VALUES (
                        :id, :airport, :type, :description, :frequency_mhz
                    );
                """, row)

            database.commit()
            database.close()
            logger.info("Frequencies updated !")

    @classmethod
    @lru_cache(maxsize=None)
    def from_airport_id(cls, id: int):

        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()
        cursor.execute("SELECT * FROM frequencies WHERE airport = ?", (id,))

        frequencies_list = []
        for row in cursor.fetchall():
            frequencies_list.append(Frequency(dict(row)))

        database.close()

        return frequencies_list

    def __init__(self, data):
        self.data = data

    def __str__(self):
        return f"Frequency({self.data["type"]} {self.data["frequency_mhz"]:.3f})"

    def __repr__(self):
        return str(self)
