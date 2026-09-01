
import os.path
import sqlite3

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

    @property
    def id(self):
        return self.data["id"]

    @property
    def name(self):
        return self.data["name"]

    @property
    def icao_code(self):
        if self.data["icao_code"]:
            return self.data["icao_code"]
        else:
            return self.data["ident"]

    @property
    def position(self):
        return self.data["position"]
    
    @property
    def continent(self):
        return continent[self.data["continent"]]

    @property
    def municipality(self):
        return self.data["municipality"]

    @property
    def current_weather(self):
        return OpenMeteo.current(self.position)
