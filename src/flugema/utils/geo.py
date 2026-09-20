import math
import datetime
import gpxpy
import json
import os
import hashlib
import io

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

NICEGUI_STORAGE_PATH = os.environ.get('NICEGUI_STORAGE_PATH', '.nicegui')
GEOPATHS_DATA_DIR = os.path.join(NICEGUI_STORAGE_PATH, "geo-paths")

class GeoPos:

    @classmethod
    def from_serialized(cls, data):
        return GeoPos(data["latitude"], data["longitude"], data["altitude"], data["groud-altitude"], data["date"])

    def __init__(self, 
        latitude: float, 
        longitude: float, 
        altitude: float | None = None, 
        groud_altitude: float | None = None, 
        date: datetime.datetime | None = None, 
        accuracy: float | None = None
    ):
        self._lat = latitude
        self._lon = longitude
        self._alt = altitude
        self._gnd_alt = groud_altitude
        self._date = date
        self._accuracy = accuracy

    def __repr__(self):
        return f"GeoPos({self._lat}, {self._lon}, {self._alt})"
    
    def __format__(self, format_spec):
        
        if format_spec == "deg": # Format : DD.DDDDDD [NS] DD.DDDDDD [EW]
            lat_dir = "N" if self._lat >= 0 else "S"
            lon_dir = "E" if self._lon >= 0 else "W"
            return f"{abs(self._lat):.6f} {lat_dir} {abs(self._lon):.6f} {lon_dir}"
        elif format_spec == "min": # Format : DD° MM.MMM' [NS] DD° MM.MMM' [EW]
            # Latitude
            lat_deg = int(abs(self._lat))
            lat_min = (abs(self._lat) - lat_deg) * 60
            lat_dir = "N" if self._lat >= 0 else "S"
            # Longitude
            lon_deg = int(abs(self._lon))
            lon_min = (abs(self._lon) - lon_deg) * 60
            lon_dir = "E" if self._lon >= 0 else "W"
            # Format
            return f"{lat_deg}° {lat_min:06.3f}' {lat_dir} {lon_deg}° {lon_min:06.3f}' {lon_dir}"
        elif format_spec == "sec": # Format : DD° MM' SS.S'' [NS] DD° MM' SS.S'' [EW]
            # Latitude
            lat_deg = int(abs(self._lat))
            lat_min_full = (abs(self._lat) - lat_deg) * 60
            lat_min = int(lat_min_full)
            lat_sec = (lat_min_full - lat_min) * 60
            lat_dir = "N" if self._lat >= 0 else "S"
            # Longitude
            lon_deg = int(abs(self._lon))
            lon_min_full = (abs(self._lon) - lon_deg) * 60
            lon_min = int(lon_min_full)
            lon_sec = (lon_min_full - lon_min) * 60
            lon_dir = "E" if self._lon >= 0 else "W"
            # Format
            return (f"{lat_deg}° {lat_min}' {lat_sec:.1f}\" {lat_dir} "
                    f"{lon_deg}° {lon_min}' {lon_sec:.1f}\" {lon_dir}")
        else: # Format [-]xx.xxxxxx [-]yy.yyyyyy
            return f"{self._lat:.6} {self._lon:.6}"

    def __str__(self):
        if self._accuracy:
            return f"{self:deg} (±{self._accuracy} m)"
        else:
            return f"{self:deg}"

    @property
    def raw(self):
        return (self._lat, self._lon, self._alt)
    
    @property
    def serialized(self):
        
        if type(self.date) == datetime.datetime:
            date = self.date.isoformat()
        else:
            date = self.date

        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude(),
            "groud-altitude": self.gnd_altitude(),
            "date": date
        }

    @property
    def latitude(self):
        return self._lat
    
    @property
    def longitude(self):
        return self._lon

    @property
    def date(self):
        return self._date

    
    def altitude(self, unit="m"):
        if self._alt != None:
            if unit == "m":
                return self._alt
            elif unit == "ft":
                return self._alt / 0.3048
            else:
                raise ValueError("Unsupported unit. Use 'm' or 'ft'.")
        else:
            return None

    def gnd_altitude(self, unit="m"):
        if self._gnd_alt != None:
            if unit == "m":
                return self._gnd_alt
            elif unit == "ft":
                return self._gnd_alt / 0.3048
            else:
                raise ValueError("Unsupported unit. Use 'm' or 'ft'.")
        else:
            return None
    
    def distance_to(self, other: "GeoPos", unit="m") -> float:
        from math import radians, sin, cos, sqrt, atan2

        # Rayon moyen de la Terre en mètres
        R = 6371000

        # Conversion des coordonnées en radians
        lat1_rad = radians(self._lat)
        lon1_rad = radians(self._lon)
        lat2_rad = radians(other._lat)
        lon2_rad = radians(other._lon)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        # Distance au sol en mètres
        ground_distance = R * c

        # Prise en compte de l'altitude
        try:
            delta_alt = other._alt - self._alt
            total_distance = sqrt(ground_distance**2 + delta_alt**2)
        except:
            total_distance = ground_distance

        if unit == "km":
            return total_distance / 1000
        elif unit == "nm":
            return total_distance / 1852
        else:  # mètres
            return total_distance
    
    def heading_to(self, other: "GeoPos") -> float:
        from math import radians, degrees, sin, cos, atan2

        lat1_rad = radians(self._lat)
        lon1_rad = radians(self._lon)
        lat2_rad = radians(other._lat)
        lon2_rad = radians(other._lon)

        dlon = lon2_rad - lon1_rad

        x = sin(dlon) * cos(lat2_rad)
        y = cos(lat1_rad) * sin(lat2_rad) - (sin(lat1_rad) * cos(lat2_rad) * cos(dlon))

        initial_bearing = atan2(x, y)
        initial_bearing = degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360

        return compass_bearing

class GeoPath():

    @classmethod
    def from_gpx(cls, xml_file: io.StringIO):

        gpx = gpxpy.parse(xml_file)
        data = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    date = point.time
                    latitude = point.latitude
                    longitude = point.longitude
                    altitude = point.elevation
                    gnd_altitude = None

                    if point.description:
                        try:
                            desc_data = json.loads(point.description)
                            gnd_altitude = desc_data["ele"]
                        except:
                            pass

                    data.append(GeoPos(latitude, longitude, altitude=altitude, groud_altitude=gnd_altitude, date=date))

        logger.debug(f"New GeoPath from GPX created (len={len(data)})")
        return GeoPath(data)

    @classmethod
    def from_storage(cls, file):
        file_path = os.path.join(GEOPATHS_DATA_DIR, file)

        with open(file_path, "r") as file:
            data = []
            for pos in json.load(file):
                data.append(GeoPos.from_serialized(pos))

        return GeoPath(data)

    def __init__(self, data):
        self.data = data

    def to_storage(self):

        str_data = json.dumps(self.serialized)

        file_name = hashlib.sha1(str_data.encode("utf-8")).hexdigest() + ".json"
        file_path = os.path.join(GEOPATHS_DATA_DIR, file_name)

        with open(file_path, "w") as geo_file:
            geo_file.write(str_data)

        logger.debug(f"Save file {file_name} to storage")

        return file_name

    @property
    def serialized(self):
        serialized_data = []

        for point in self.data:
            serialized_data.append(point.serialized)

        return serialized_data

    @property
    def time_list(self):
        date_list = []

        for point in self.data:
            if point.date != None:
                date_list.append(point.date)
            else:
                return None

        return date_list

    @property
    def position_list(self):
        pos_list = []

        for point in self.data:
            pos_list.append(point.raw)

        return pos_list

    def altitudes_list(self, unit="m"):
        alt_list = []

        for point in self.data:
            if point.altitude == None:
                return None
            alt_val = point.altitude(unit=unit)
            alt_list.append(alt_val)

        return alt_list

    def ground_altitudes_list(self, unit="m"):
        alt_list = []

        for point in self.data:
            if point.gnd_altitude == None:
                return None
            alt_val = point.gnd_altitude(unit=unit)
            alt_list.append(alt_val)

        return alt_list

    def get_bounds(self):

        min_lat = 90
        max_lat = -90

        min_lon = 180
        max_lon = -180

        for point in self.data:

            if point.latitude > max_lat:
                max_lat = point.latitude
            if point.latitude < min_lat:
                min_lat = point.latitude
            if point.longitude > max_lon:
                max_lon = point.longitude
            if point.longitude < min_lon:
                min_lon = point.longitude

        return [(min_lat, min_lon), (max_lat, max_lon)]