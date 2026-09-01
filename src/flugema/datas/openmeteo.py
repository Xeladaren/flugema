import http.client
import urllib
import json

from ..utils.geo import GeoPos

# /v1/forecast;latitude=47.0821&longitude=-0.877064&current=temperature_2m,relative_humidity_2m,is_day,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m,apparent_temperature,rain,showers,snowfall,weather_code,cloud_cover,pressure_msl,surface_pressure&wind_speed_unit=kn
# /v1/forecast?latitude=52.5200&longitude=13.410000&current=temperature_2m,relative_humidity_2m,is_day,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m,apparent_temperature,rain,showers,snowfall,weather_code,cloud_cover,pressure_msl,surface_pressure&wind_speed_unit=kn

class OpenMeteo():

    HOST = "api.open-meteo.com"

    @classmethod
    def _get(cls, params):
        query = urllib.parse.urlencode(params, safe=",")
        url = urllib.parse.urlunparse(("", "", "/v1/forecast", "", query, ""))

        connect = http.client.HTTPSConnection(OpenMeteo.HOST)
        connect.request("GET", url)
        response = connect.getresponse()

        if response.status == 200:
            return json.load(response)
        else:
            return None

    @classmethod
    def current(cls, pos: GeoPos):

        VARIABLES = [
            "temperature_2m",
            "relative_humidity_2m",
            "is_day",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "apparent_temperature",
            "rain",
            "showers",
            "snowfall",
            "weather_code",
            "cloud_cover",
            "pressure_msl",
            "surface_pressure",
        ]

        params = {
            "latitude": pos.latitude,
            "longitude": pos.longitude,
            "current": ",".join(VARIABLES),
            "wind_speed_unit": "kn",
        }

        value = OpenMeteo._get(params)

        if value:
            return value["current"]
        else:
            return None

    @classmethod
    def weather_picture(cls, weather_code: int, day: bool = True) -> str:
        icon_name = "not-available"

        # icons from https://meteocons.com/

        codes_value = [
            ([0],               "clear-day",                        "clear-night"),
            ([1],               "mostly-clear-day",                 "mostly-clear-night"),
            ([2],               "partly-cloudy-day",                "partly-cloudy-night"),
            ([3],               "overcast",                         None),
            ([45, 48],          "fog-day",                          "fog-night"),
            ([51],              "drizzle",                          None),
            ([53],              "overcast-drizzle",                 None),
            ([55],              "extreme-drizzle",                  None),
            ([56, 57, 66, 67],  "sleet",                            None),
            ([61],              "rain",                             None),
            ([63],              "overcast-rain",                    None),
            ([65],              "extreme-rain",                     None),
            ([71, 77],          "snow",                             None),
            ([73],              "overcast-snow",                    None),
            ([75],              "extreme-snow",                     None),
            ([80],              "mostly-clear-day-rain",            "mostly-clear-night-rain"),
            ([81],              "overcast-day-rain",                "overcast-night-rain"),
            ([82],              "extreme-day-rain",                 "extreme-night-rain"),
            ([85],              "mostly-clear-day-snow",            "mostly-clear-night-snow"),
            ([86],              "overcast-day-snow",                "overcast-night-snow"),
            ([95],              "thunderstorms-extreme-day",        "thunderstorms-extreme-night"),
            ([96, 99],          "thunderstorms-extreme-day-hail",   "thunderstorms-extreme-night-hail"),
        ] 

        for codes, icon_day, icon_night in codes_value:
            if weather_code in codes:
                icon_name = icon_day if day or not icon_night else icon_night
                return f"/weather-icons/{icon_name}.svg"
