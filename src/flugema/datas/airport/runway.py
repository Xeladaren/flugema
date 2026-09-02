import csv
import datetime
import http.client
import io
import os.path
import sqlite3
import urllib
import drawsvg
import math
from io import StringIO

from functools import lru_cache

from .ourairports import OurAirports

import logging
logger = logging.getLogger(__name__)

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
DATABASE_PATH = os.path.join(NICEGUI_STORAGE_PATH, "database.db")

class Runway():

    @classmethod
    def update(cls):

        reader = OurAirports.runways()
        if reader:
            
            database = sqlite3.connect(DATABASE_PATH)
            cursor = database.cursor()

            cursor.execute("DROP TABLE IF EXISTS runways;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runways (
                    id INTEGER PRIMARY KEY,
                    airport INTEGER NOT NULL,
                    surface TEXT,
                    lighted BOOLEAN NOT NULL DEFAULT FALSE,
                    closed BOOLEAN NOT NULL DEFAULT FALSE,
                    le_ident TEXT,
                    he_ident TEXT,
                    length REAL,
                    width REAL,
                    le_latitude REAL,
                    le_longitude REAL,
                    le_elevation REAL,
                    le_heading REAL,
                    le_displaced_threshold REAL,
                    he_latitude REAL,
                    he_longitude REAL,
                    he_elevation REAL,
                    he_heading REAL,
                    he_displaced_threshold REAL,

                    FOREIGN KEY (airport) REFERENCES airports(id)
                );
            """)

            for row in reader:

                for elem in row:
                    if row[elem] == "":
                        row[elem] = None

                row['id'] = int(row['id'])
                row['airport'] = int(row['airport_ref'])

                del row['airport_ref']
                del row['airport_ident']

                for elem in list(row.keys()):
                    if "_ft" in elem:
                        if row[elem]:
                            row[elem.replace("_ft", "")] = float(row[elem]) / 3.28084
                        else:
                            row[elem.replace("_ft", "")] = None
                        del row[elem]

                    if "_deg" in elem:
                        new_elem = elem.replace("_degT", "")
                        new_elem = new_elem.replace("_deg", "")
                        if row[elem]:
                            row[new_elem] = float(row[elem])
                        else:
                            row[new_elem] = None
                        del row[elem]


                for elem in ["closed", "lighted"]:
                    row[elem] = row[elem] == "1"

                cursor.execute("""
                    INSERT INTO runways (
                        id, airport, surface, lighted, closed,
                        le_ident, he_ident, length, width,
                        le_latitude, le_longitude, le_elevation, le_heading, le_displaced_threshold,
                        he_latitude, he_longitude, he_elevation, he_heading, he_displaced_threshold
                    ) VALUES (
                        :id, :airport, :surface, :lighted, :closed,
                        :le_ident, :he_ident, :length, :width,
                        :le_latitude, :le_longitude, :le_elevation, :le_heading, :le_displaced_threshold,
                        :he_latitude, :he_longitude, :he_elevation, :he_heading, :he_displaced_threshold
                    );
                """, row)

            database.commit()
            database.close()
            logger.info("Runway updated !")

    @classmethod
    @lru_cache(maxsize=None)
    def from_airport_id(cls, id: int):

        database = sqlite3.connect(DATABASE_PATH)
        database.row_factory = sqlite3.Row
        cursor = database.cursor()
        cursor.execute("SELECT * FROM runways WHERE airport = ?", (id,))

        runway_list = []
        for row in cursor.fetchall():
            runway_list.append(Runway(dict(row)))

        database.close()

        return runway_list

    def __init__(self, data):
        self.data = data

    def __str__(self):
        return f"Runway({self.data["le_ident"]}-{self.data["he_ident"]})"

    def __repr__(self):
        return str(self)

    def __getattr__(self, name: str):
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"Attribut '{name}' not found.")

    def trace_runway(self, wind_dir: int | None = None):

        draw = drawsvg.Drawing(200, 200, origin='center')
        runway_group = drawsvg.Group(transform=f"rotate({self.le_heading} 0 0)")

        runway_group.append(drawsvg.Rectangle(-20, -90, 40, 180, fill='#202020', stroke='#EEEEEE'))
        runway_group.append(drawsvg.Line(0, -40, 0, 40, stroke_width=2, stroke='#EEEEEE', stroke_dasharray="6, 6"))

        le_group = drawsvg.Group(transform="rotate(0 0 0)")
        he_group = drawsvg.Group(transform="rotate(180 0 0)")

        
        le_group.append(drawsvg.Text(self.le_ident, x=0, y=60, text_anchor='middle', font_size=20, fill='#EEEEEE'))
        he_group.append(drawsvg.Text(self.he_ident, x=0, y=60, text_anchor='middle', font_size=20, fill='#EEEEEE'))

        for pos in [-10, -4, 4, 10]:
            le_group.append(drawsvg.Line(pos, 80, pos, 65, stroke_width=3, stroke='#EEEEEE'))
            he_group.append(drawsvg.Line(pos, 80, pos, 65, stroke_width=3, stroke='#EEEEEE'))

        runway_group.append(le_group)
        runway_group.append(he_group)
        draw.append(runway_group)

        if wind_dir != None:

            wind_tail = drawsvg.Marker(0, 0, 1, 1, scale=1, orient="auto-start-reverse", overflow="visible")
            wind_tail.append(drawsvg.Path(
                fill="none", 
                stroke="context-stroke", 
                stroke_width=0.8, 
                stroke_linecap="round")
                .m(-2, -2).append('', -2, 2).append('', 2, 2)
                .M(0, -2).append('', -2, 0).append('', 0, 2)
                .M(2, 2).append('', 0, 0).append('', 2, -2)
            )

            x =  70 * math.sin(math.radians(wind_dir))
            y =  -70 * math.cos(math.radians(wind_dir))
            draw.append(drawsvg.Line(0, 0, x, y, marker_end=wind_tail, stroke_width=2, stroke='#0088FF', stroke_linecap="round"))

        data = StringIO()
        draw.as_svg(data, header="")

        return data.getvalue().replace("\n", "")
