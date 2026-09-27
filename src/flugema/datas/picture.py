
import os
import sqlite3
import datetime
import PIL.Image
import PIL.ExifTags
import uuid
import mimetypes

from functools import lru_cache

from ..utils.geo import GeoPos

import logging
logger = logging.getLogger(__name__)

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")
PIC_DIR = os.path.join(NICEGUI_STORAGE_PATH, "pictures")

class Picture():

    @classmethod
    def create_database(cls):

        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pictures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id INTEGER NOT NULL,
                datetime DATETIME NOT NULL,
                path TEXT NOT NULL,
                latitude REAL,
                longitude REAL,

                FOREIGN KEY (flight_id)  REFERENCES flights(id)
            );
        """)

        database.commit()
        database.close()

    @classmethod
    def new_path(cls, file_type="image/jpeg"):
        extention = mimetypes.guess_extension(file_type)
        file_name = f"{uuid.uuid1()}{extention}"

        if not os.path.isdir(PIC_DIR):
            os.makedirs(PIC_DIR, mode=0o700, exist_ok=True)

        return os.path.join(PIC_DIR, file_name)

    @classmethod
    def _get_exif_tags(cls, path):
        image = PIL.Image.open(path)
        img_exif = image._getexif()
        data = {}

        if img_exif:
            for tag_id in img_exif:
                tag = PIL.ExifTags.TAGS.get(tag_id, tag_id)
                data[tag] = img_exif[tag_id]

        return data

    @classmethod
    def _get_datetime(cls, tags):
        if "DateTimeOriginal" in tags:
            date_raw = tags["DateTimeOriginal"]
        elif "DateTimeDigitized" in tags:
            date_raw = tags["DateTimeDigitized"]
        elif "DateTime" in tags:
            date_raw = tags["DateTime"]
        else:
            return datetime.datetime.now(tz=datetime.UTC)

        if "OffsetTimeOriginal" in tags:
            date_raw += tags["OffsetTimeOriginal"]
        elif "OffsetTime" in tags:
            date_raw += tags["OffsetTime"]

        date_raw = date_raw.replace(" ", "T")
        date_raw = date_raw[:10].replace(":", "-") + date_raw[10:]

        date_local = datetime.datetime.fromisoformat(date_raw)
        return date_local.astimezone(tz=datetime.UTC)

    @classmethod
    def _get_position(cls, tags):
        if "GPSInfo" in tags:
            gps_info = tags["GPSInfo"]

            if 2 in gps_info:
                lat_data = gps_info[2]
                lat = lat_data[0] + (lat_data[1] / 60.0) + (lat_data[2] / 3600.0)
                if 1 in gps_info and gps_info[1] == "S":
                    lat = -lat
            else:
                return None

            if 4 in gps_info:
                long_data = gps_info[4]
                long = long_data[0] + (long_data[1] / 60.0) + (long_data[2] / 3600.0)
                if 3 in gps_info and gps_info[3] == "W":
                    long = -long
            else:
                return None

            return GeoPos(lat, long)
        else:
            return None

    @classmethod
    def add(cls, flight, path):

        tags = cls._get_exif_tags(path)
        date = Picture._get_datetime(tags)
        position = Picture._get_position(tags)

        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        if position:
            data = (flight.id, date, path, position.latitude, position.longitude)
        else:
            data = (flight.id, date, path, None, None)
    
        cursor.execute("""
            INSERT INTO pictures (
                flight_id, datetime, path, latitude, longitude
            ) VALUES (
                ?, ?, ?, ?, ?
            )
        """, data)
        new_id = cursor.lastrowid

        database.commit()
        database.close()

        return Picture.from_id(new_id)

    @classmethod
    def from_flight(cls, flight):
        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()
        picture_list = []

        cursor.execute("SELECT id FROM pictures WHERE flight_id = ? ORDER BY datetime ASC", (flight.id,))
        for result in cursor.fetchall():
            picture_list.append(Picture.from_id(result[0]))

        database.commit()
        database.close()
        
        return picture_list

    @classmethod
    @lru_cache(maxsize=None)
    def from_id(cls, id: int):
        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()

        cursor.execute("SELECT * FROM pictures WHERE id = ?", (id,))
        result = cursor.fetchone()

        database.commit()
        database.close()

        if result:
            return Picture(dict(result))
        else:
            return None

    def __init__(self, data):
        from ..datas import Flight

        data["flight"] = Flight.from_id(data["flight_id"])
        data["datetime"] = datetime.datetime.fromisoformat(data["datetime"])

        if data["latitude"] and data["longitude"]:
            data["position"] = GeoPos(data["latitude"], data["longitude"])
        else:
            data["position"] = None

        del data["flight_id"]
        del data["latitude"]
        del data["longitude"]

        self._data = data

    def __getattr__(self, name: str):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Attribut '{name}' not found.")

    @property
    def file_name(self):
        file_ext = os.path.splitext(self.path)[1]
        date_str = self.datetime.strftime("%Y%m%d_%H%M%SZ")
        departure = self.flight.departure.ident
        arrival = self.flight.arrival.ident

        return f"{date_str}_{departure}_{arrival}{file_ext}"

    @property
    def url(self):
        return f"/picture/{self.id}"

    def remove(self):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("DELETE FROM pictures WHERE id = ?;", (self.id,))

        database.commit()
        database.close()

        os.remove(self.path)

        del self._data
        del self