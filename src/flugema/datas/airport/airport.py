
import os.path
import sqlite3
import datetime

from functools import lru_cache

from .country       import Country, continent
from .region        import Region
from .runway        import Runway
from .frequency     import Frequency
from .ourairports   import OurAirports

from ..openmeteo import OpenMeteo
from ...utils.geo import GeoPos

import logging
logger = logging.getLogger(__name__)

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")

class Airport():

    @classmethod
    def update(cls):

        reader = OurAirports.airports()
        if reader:

            database = sqlite3.connect(DATABASE_PATH)
            cursor = database.cursor()

            cursor.execute("DROP TABLE IF EXISTS airports;")
            cursor.execute("""
                CREATE TABLE airports (
                    id INTEGER PRIMARY KEY,
                    ident TEXT NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    elevation REAL,
                    continent TEXT,
                    iso_country TEXT,
                    iso_region TEXT,
                    municipality TEXT,
                    scheduled_service BOOLEAN DEFAULT FALSE,
                    icao_code TEXT,
                    iata_code TEXT,
                    gps_code TEXT,
                    local_code TEXT,
                    home_link TEXT,
                    wikipedia_link TEXT,
                    keywords TEXT
                );
            """)

            for row in reader:

                for elem in row:
                    if row[elem] == "":
                        row[elem] = None

                row["id"] = int(row["id"])
                row["latitude"] = float(row["latitude_deg"])
                row["longitude"] = float(row["longitude_deg"])
                row["scheduled_service"] = row["scheduled_service"]  == 'yes'

                if row["elevation_ft"]:
                    # convert into SI unit meter
                    row["elevation"] = float(row["elevation_ft"]) / 3.28084
                else:
                    row["elevation"] = None

                del row["latitude_deg"]
                del row["longitude_deg"]
                del row["elevation_ft"]

                cursor.execute("""
                    INSERT INTO airports (
                        id, ident, type, name, latitude, longitude, elevation,
                        continent, iso_country, iso_region, municipality, scheduled_service,
                        icao_code, iata_code, gps_code, local_code, home_link, wikipedia_link, keywords
                    ) VALUES (
                        :id, :ident, :type, :name, :latitude, :longitude, :elevation,
                        :continent, :iso_country, :iso_region, :municipality, :scheduled_service,
                        :icao_code, :iata_code, :gps_code, :local_code, :home_link, :wikipedia_link, :keywords
                    );
                """, row)

            database.commit()
            database.close()
            logger.info("Airports updated !")

    @classmethod
    def from_icao(cls, icao_code: str):

        database = sqlite3.connect(DATABASE_PATH)

        cursor = database.cursor()
        cursor.execute("SELECT id FROM airports WHERE ident = :code OR icao_code = :code OR gps_code = :code", {"code": icao_code})
        result = cursor.fetchone()

        database.close()

        return Airport.from_id(result[0]) if result else None

    @classmethod
    @lru_cache(maxsize=None)
    def from_id(cls, airport_id: int):

        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row

        cursor = database.cursor()
        cursor.execute("SELECT * FROM airports WHERE id = :id", {"id": airport_id})
        result = cursor.fetchone()

        database.close()

        return Airport(dict(result)) if result else None
    
    @classmethod
    def nearest(cls, pos: GeoPos, icao_only: bool = False) -> Airport | None:
        database = sqlite3.connect(DATABASE_PATH)

        cursor = database.cursor()
        cursor.execute("SELECT id, latitude, longitude, icao_code FROM airports")

        nearest_dist = None
        nearest_id = None

        for result in cursor.fetchall():
            if not icao_only or not result[3] is None:
                res_pos = GeoPos(result[1], result[2])
                distance_to = pos.distance_to(res_pos)
                if nearest_dist == None or nearest_dist > distance_to:
                        nearest_dist = distance_to
                        nearest_id = result[0]

        database.close()

        return Airport.from_id(nearest_id) if nearest_id else None

    def __init__(self, data):

        data["id"] = int(data["id"])
        data["position"] = GeoPos(data["latitude"], data["longitude"], data["elevation"])

        del data["latitude"]
        del data["longitude"]
        del data["elevation"]

        self.data = data
        self.runways = Runway.from_airport_id(data["id"])
        self.freqencies = Frequency.from_airport_id(data["id"])
        self.region = Region.from_iso_code(data["iso_region"])
        self.country = Country.from_iso_code(data["iso_country"])

        self._current_weather = None
        self._current_astro = None

    def __eq__(self, other):
        if type(other) == int:
            return self.data["id"] == other
        elif type(other) == str:
            return  self.data["ident"] == other or self.data["icao_code"] == other or self.data["iata_code"] == other or self.data["gps_code"] == other
        elif type(other) == Airport:
            return self.data["id"] == other.data["id"]

    def __str__(self):
        return f"{self.icao_code} - {self.name}"

    def __repr__(self):
        return f"Airport(id={self.id}, ident={self.data["ident"]})"

    def __getattr__(self, name: str):
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"Attribut '{name}' not found.")

    @property
    def icao_code(self):
        if self.data["icao_code"]:
            return self.data["icao_code"]
        else:
            return self.data["ident"]
    
    @property
    def continent(self):
        return continent[self.data["continent"]]

    @property
    def current_weather(self):

        if not self._current_weather:
            self._current_weather = OpenMeteo.current(self.position)
            logger.info(f"Get new weather info to {self.icao_code} ({self._current_weather['time']}Z)")
        else:
            date_now     = datetime.datetime.now(tz=datetime.UTC)
            date_expire  = datetime.datetime.fromisoformat(self._current_weather["time"]+"Z")
            date_expire += datetime.timedelta(seconds=self._current_weather["interval"])

            if date_now > date_expire:
                self._current_weather = OpenMeteo.current(self.position)
                logger.info(f"Get new weather info to {self.icao_code} ({self._current_weather['time']}Z)")

        return self._current_weather


    def astro_info(self, start_date: str | None = None, stop_date: str | None = None):
        return OpenMeteo.astro_infos(self.position, start_date, stop_date)

    def current_astro(self):
        if not self._current_astro:
            self._current_astro = self.astro_info()
            logger.info(f"Get new astro info to {self.icao_code} ({self._current_astro['time'][0]})")

        else:
            date_now = datetime.datetime.now(tz=datetime.UTC).date()
            date_astro = datetime.date.fromisoformat(self._current_astro["time"][0])

            if date_now > date_astro:
                self._current_astro = self.astro_info()
                logger.info(f"Get new astro info to {self.icao_code}")

        return self._current_astro

    def best_runway(self, wind_speed: float, wind_dir: float) -> Runway | None:

        if len(self.runways) == 0:
            return None

        best_runway = None
        best_crosswind = 10000

        for runway in self.runways:
            if not runway.closed and runway.le_heading != None and runway.he_heading != None:
                _, _, crosswind = runway.cross_wind(wind_speed, wind_dir)
                if crosswind < best_crosswind:
                    best_runway = runway
                    best_crosswind = crosswind

        return best_runway

    def distance_to(self, other: Airport | GeoPos, unit="m"):
        if type(other) == Airport:
            return self.position.distance_to(other.position, unit=unit)
        elif type(other) == GeoPos:
            return self.position.distance_to(other, unit=unit)
        else:
            raise TypeError("Invalid Positon type (need Airport or GeoPos)")
