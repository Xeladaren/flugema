
import os
import sqlite3
import datetime

from nicegui import app, context
from argon2 import PasswordHasher

from functools import lru_cache

from ..utils.geo import GeoPos
from ..utils.time import datetime_from_db_str
from ..datas.airport import Airport

import logging
logger = logging.getLogger(__name__)

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")

ph = PasswordHasher(
    time_cost=3,       # Nombre d'itérations (augmente le temps de calcul)
    memory_cost=65536, # Utilisation mémoire (en Ko)
    parallelism=4,     # Nombre de threads
    hash_len=32,       # Longueur du hash
    salt_len=16        # Longueur du sel
)

class User():

    @classmethod
    def create_database(cls):
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                home_airport INTEGER,
                role TEXT NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                openapi_apikey TEXT,

                CHECK (username != '' AND length(username) >= 3),
                CHECK (email LIKE '%_@__%.__%'),

                FOREIGN KEY (home_airport) REFERENCES airports(id)
            );
        """)

        database.commit()
        database.close()

    @classmethod
    @lru_cache(maxsize=None)
    def from_id(cls, user_id: int):
        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()

        cursor.execute("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id})
        result = cursor.fetchone()

        database.commit()
        database.close()

        if result:
            return User(dict(result))
        else:
            return None

    @classmethod
    def from_storage(cls):
        if app.storage.user.get('authenticated', False):
            return User.from_id(app.storage.user["user_id"])
        else:
            return None

    @classmethod
    def login(cls, login, password):
        """
        Get user objet if login/password is checked.
        """
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("SELECT id, password_hash, is_active FROM users WHERE username = :login OR email = :login", {"login": login})
        result = cursor.fetchone()

        if result:
            user_id, password_hash, is_active = result

            if is_active:
                try:
                    ph.verify(password_hash, password)
                    user = User.from_id(user_id)
                    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
                except:
                    user = None
            else:
                user = None
        else:
            user = None

        ip_client = context.client.request.client.host

        if user:
            logger.info(f"Connection of '{user}' from {ip_client}")
        else:
            logger.warn(f"Invalid connection of '{login}' from {ip_client}")

        database.commit()
        database.close()

        return user

    @classmethod
    def new_user(cls, username, password, email, full_name=None, home_airport=None):
        
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        password_hash = ph.hash(password)

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, home_airport)
            VALUES (?, ?, ?, ?, ?)
        """, (username, email, password_hash, full_name, home_airport.id if home_airport else None))

        database.commit()
        database.close()

    @classmethod
    def username_exist(cls, username: str) -> bool:
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ?", [username])
        result = cursor.fetchone()

        database.commit()
        database.close()

        return result != None

    @classmethod
    def email_exist(cls, email: str) -> bool:
        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", [email])
        result = cursor.fetchone()

        database.commit()
        database.close()

        return result != None


    def __init__(self, data):
        
        data["created_at"] = datetime_from_db_str(data["created_at"])
        data["last_login"] = datetime_from_db_str(data["last_login"])
        data["home_airport"] = Airport.from_id(data["home_airport"]) if data["home_airport"] else None

        self.data = data

    def __str__(self):
        return self.data["username"]

    def __repr__(self):
        return f"User(id={self.id}, username={self.username}, role={self.role})"

    def __eq__(self, other):
        return self.id == other.id

    def _update_value(self, name: str, value: str, local_value: None = None):

        self.data[name] = local_value if local_value != None else value

        database = sqlite3.connect(DATABASE_PATH)
        cursor = database.cursor()

        cursor.execute(f"UPDATE users SET {name} = ? WHERE id = ?", (value, self.id))

        database.commit()
        database.close()

    @property
    def id(self):
        return self.data["id"]

    @property
    def username(self) -> str:
        return self.data["username"]

    @username.setter
    def username(self, value: str) -> None:
        self._update_value("username", value)

    @property
    def email(self) -> str:
        return self.data["email"]

    @email.setter
    def email(self, value: str) -> None:
        self._update_value("email", value)

    @property
    def full_name(self) -> str:
        return self.data["full_name"]

    @full_name.setter
    def full_name(self, value: str) -> None:
        self._update_value("full_name", value)

    @property
    def openapi_apikey(self) -> str:
        return self.data["openapi_apikey"]

    @openapi_apikey.setter
    def openapi_apikey(self, value: str) -> None:
        self._update_value("openapi_apikey", value)

    @property
    def is_active(self) -> bool:
        return bool(self.data["is_active"])

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._update_value("is_active", value)

    @property
    def role(self) -> str:
        return self.data["role"]

    @role.setter
    def role(self, value: str) -> None:
        if value in ["user", "admin"]:
            self._update_value("role", value)
        else:
            raise ValueError("Invalid user role.")

    @property
    def home_airport(self) -> Airport:
        return self.data["home_airport"]

    @home_airport.setter
    def home_airport(self, value: Airport) -> None:
        self._update_value("home_airport", value.id if value else None, local_value=value)

    def set_password(self, old_password: str, new_password: str, force: bool = False):
        try:
            if not force:
                password_hash = self.data["password_hash"]
                ph.verify(password_hash, old_password)
            password_hash = ph.hash(new_password)
            self._update_value("password_hash", password_hash)

            return True
        except:
            return False

    @property
    def flights(self):
        from .flight import Flight
        return Flight.get_user_flights(self.id)

    def flights_stats(self):
        from .flight import Flight

        stats = {
            "durations" : {
                "total": 0,
                "contition": {
                    "day": 0,
                    "night": 0,
                    "ifr": 0
                },
                "function":{
                    "pic": 0,
                    "copilote": 0,
                    "dual": 0,
                    "instructor": 0
                }
            },
            "landings":{
                "day": 0,
                "night": 0
            },
            "apch_ifr": 0,
            "airports": [],
            "farthest-airport": None
        }

        for flight in self.flights:
            stats['durations']['total'] += flight.total_min
            stats['durations']['contition']['day'] += (flight.total_min - flight.night_min)
            stats['durations']['contition']['night'] += flight.night_min
            stats['durations']['contition']['ifr'] += flight.ifr_min
            stats['durations']['function'][flight.role] += flight.total_min

            stats['landings']['day'] += flight.ldg_day
            stats['landings']['night'] += flight.ldg_night
            stats['apch_ifr'] += flight.apch_ifr

            if not flight.departure in stats['airports']:
                stats['airports'].append(flight.departure)

            if not flight.arrival in stats['airports']:
                stats['airports'].append(flight.arrival)

            for touch in flight.touch_and_go:
                if not touch['airport'] in stats['airports']:
                    stats['airports'].append(touch['airport'])

        for airport in stats['airports']:
            if stats['farthest-airport']:
                if airport.distance_to(self.home_airport) > stats['farthest-airport'].distance_to(self.home_airport):
                    stats['farthest-airport'] = airport
            else:
                stats['farthest-airport'] = airport

        return stats

