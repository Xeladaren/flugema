
import os
import sqlite3
import datetime
import json

from copy import deepcopy
from functools import lru_cache

from ..utils.geo import GeoPath
from ..utils.time import formated_min

from .airport import Airport
from .airplane import Airplane
from .users import User

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")


class Flight():

    ROLES = {
        "pic": "Pilot-In-Command",
        "copilote": "Copilot",
        "dual": "Dual",
        "instructor": "Instructor"
    }

    @classmethod
    def create_database(cls):

        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                departure_id INTEGER NOT NULL,
                departure_time DATETIME NOT NULL,
                arrival_id INTEGER NOT NULL,
                arrival_time DATETIME NOT NULL,
                airplane_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                total_min INTEGER NOT NULL,
                night_min INTEGER NOT NULL DEFAULT 0,
                ifr_min INTEGER NOT NULL DEFAULT 0,
                ldg_day INTEGER NOT NULL DEFAULT 0,
                ldg_night INTEGER NOT NULL DEFAULT 0,
                apch_ifr INTEGER NOT NULL,
                pic_name TEXT NOT NULL,
                remarks TEXT,
                page_break BOOLEAN NOT NULL DEFAULT false,
                geo_path TEXT,
                touch_and_go JSONB NOT NULL,

                FOREIGN KEY (airplane_id)  REFERENCES airplanes(id),
                FOREIGN KEY (user_id)      REFERENCES users(id),
                FOREIGN KEY (departure_id) REFERENCES airports(id),
                FOREIGN KEY (arrival_id)   REFERENCES airports(id)
            );
        """)

        database.commit()
        database.close()

    @classmethod
    def _get_db_datas(cls, data):
        if not "user_id" in data:
            data["user_id"] = data["user"].id

        if not "departure_id" in data:
            data["departure_id"] = data["departure"].id

        if not "arrival_id" in data:
            data["arrival_id"] = data["arrival"].id

        if not "airplane_id" in data:
            data["airplane_id"] = data["airplane"].id

        if type(data["departure_time"]) == datetime.datetime:
            data["departure_time"] = data["departure_time"].isoformat(timespec='minutes')

        if type(data["arrival_time"]) == datetime.datetime:
            data["arrival_time"] = data["arrival_time"].isoformat(timespec='minutes')

        if type(data["touch_and_go"]) == list:
            for touch in data["touch_and_go"]:
                touch["airport_id"] = touch["airport"].id
                del touch["airport"]
            data["touch_and_go"] = json.dumps(data["touch_and_go"])

        return data
    @classmethod
    def new(cls, data):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        Flight._get_db_datas(data)

        cursor.execute("""
            INSERT INTO flights (
                user_id, departure_id, departure_time, arrival_id, arrival_time,
                airplane_id, role, total_min, night_min, ifr_min, ldg_day, ldg_night,
                apch_ifr, pic_name, remarks, page_break, geo_path, touch_and_go
            ) VALUES (
                :user_id, :departure_id, :departure_time, :arrival_id, :arrival_time,
                :airplane_id, :role, :total_min, :night_min, :ifr_min, :ldg_day, :ldg_night,
                :apch_ifr, :pic_name, :remarks, :page_break, :geo_path, :touch_and_go
            )
        """, data)
        new_id = cursor.lastrowid

        database.commit()
        database.close()

        return Flight.from_id(new_id)

    @classmethod
    @lru_cache(maxsize=None)
    def from_id(cls, id: int):
        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()

        cursor.execute("SELECT * FROM flights WHERE id = ?", (id,))
        result = cursor.fetchone()

        database.commit()
        database.close()

        if result:
            return Flight(dict(result))
        else:
            return None

    @classmethod
    def get_user_flights(cls, user_id: int) -> list:
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("SELECT id FROM flights WHERE user_id = ? ORDER BY departure_time DESC", (user_id,))
        
        flights_list = []
        for result in cursor.fetchall():
            if result:
                flight = Flight.from_id(result[0])
                flights_list.append(flight)

        database.commit()
        database.close()

        return flights_list

    def __init__(self, data):

        touch_and_go_list = json.loads(data["touch_and_go"])
        for touch_and_go in touch_and_go_list:
            touch_and_go["airport"] = Airport.from_id(touch_and_go["airport_id"])
            del touch_and_go["airport_id"]

        data["touch_and_go"]    = touch_and_go_list
        data["user"]            = User.from_id(data["user_id"])
        data["departure"]       = Airport.from_id(data["departure_id"])
        data["arrival"]         = Airport.from_id(data["arrival_id"])
        data["departure_time"]  = datetime.datetime.fromisoformat(data["departure_time"])
        data["arrival_time"]    = datetime.datetime.fromisoformat(data["arrival_time"])
        data["airplane"]        = Airplane.from_id(data["airplane_id"])
        data["page_break"]      = bool(data["page_break"])

        del data["user_id"]
        del data["airplane_id"]
        del data["departure_id"]
        del data["arrival_id"]

        self.data = data

    def __str__(self):
        return f"[{self.date}] {self.departure.icao_code} -> {self.arrival.icao_code}"

    def __repr__(self):
        return f"Flight(id={self.id}, date={self.date}, departure={repr(self.departure)}, arrival={repr(self.arrival)})"

    def remove(self):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("DELETE FROM flights WHERE id = :id;", self.data)

        database.commit()
        database.close()

        del self.data
        del self

    def formated_datas(self):
        data = self.data.copy()

        for index in ["total_min", "night_min", "ifr_min"]:
            data[index] = formated_min(data[index])

        data["date"] = self.date
        data["departure"] = self.departure.icao_code
        data["departure_time"] = self.departure_time.isoformat(timespec='minutes')
        data["arrival"] = self.arrival.icao_code
        data["arrival_time"] = self.arrival_time.isoformat(timespec='minutes')

        if self.arrival_datetime.date() != self.date:
            date_diff = self.arrival_datetime.date() - self.date
            data["arrival_time"] += f" (d+{date_diff.days})"

        data["type"] = self.airplane.type
        data["registration"] = self.airplane.registration

        del data["user"]
        del data["airplane"]
        del data["touch_and_go"]

        return data

    def update(self):

        data = deepcopy(self.data)
        data = Flight._get_db_datas(data)

        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            UPDATE flights
            SET
                departure_id = :departure_id,
                departure_time = :departure_time,
                arrival_id = :arrival_id,
                arrival_time = :arrival_time,
                airplane_id = :airplane_id,
                role = :role,
                total_min = :total_min,
                night_min = :night_min,
                ifr_min = :ifr_min,
                ldg_day = :ldg_day,
                ldg_night = :ldg_night,
                apch_ifr = :apch_ifr,
                pic_name = :pic_name,
                remarks = :remarks,
                page_break = :page_break,
                geo_path = :geo_path,
                touch_and_go = :touch_and_go
            WHERE id = :id;
        """, data)

        database.commit()
        database.close()

    @property
    def next(self):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            SELECT id FROM flights
                WHERE user_id = :user_id
                AND departure_time > :departure_time
                ORDER BY departure_time ASC
                LIMIT 1;
        """, {
            "user_id": self.user.id,
            "departure_time": self.departure_datetime.isoformat()
        })
        result = cursor.fetchone()

        database.commit()
        database.close()

        if result:
            return Flight.from_id(result[0])
        else:
            return None

    @property
    def preview(self):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            SELECT id FROM flights
                WHERE user_id = :user_id
                AND departure_time < :departure_time
                ORDER BY departure_time DESC
                LIMIT 1;
        """, {
            "user_id": self.user.id,
            "departure_time": self.departure_datetime.isoformat(timespec='minutes')
        })
        result = cursor.fetchone()

        database.commit()
        database.close()

        if result:
            return Flight.from_id(result[0])
        else:
            return None

    def __getattr__(self, name: str):
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"Attribut '{name}' not found.")

    @property
    def date(self):
        return self.data["departure_time"].date()

    @property 
    def departure_time(self):
        return self.data["departure_time"].time()

    @property
    def departure_datetime(self):
        return self.data["departure_time"]

    @property 
    def arrival_time(self):
        return self.data["arrival_time"].time()

    @property
    def arrival_datetime(self):
        return self.data["arrival_time"]

    @property
    def geo_path(self):

        if "geo_path" in self.data and self.data["geo_path"]:
            return GeoPath.from_storage(self.data["geo_path"])

        else:
            self.data["geo_path"] = None
            raw_data = []

            raw_data.append(self.departure.position)

            for tng in self.touch_and_go:
                raw_data.append(tng["airport"].position)

            raw_data.append(self.arrival.position)

            return GeoPath(raw_data)
