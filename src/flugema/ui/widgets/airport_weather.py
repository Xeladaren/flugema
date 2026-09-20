import pint
import logging
import datetime
import time
import threading

from nicegui import ui

from ...datas import User, Airport, OpenMeteo

from ...utils.weather import dew_point, pressure_altitude, density_altitude
from ...utils.time import print_hour, formated_min
from ..geoloc import Geoloc, GeolocError

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

ureg = pint.UnitRegistry()
Quantity = ureg.Quantity

class AirportWeatherWidget():

    def __init__(self, airport: Airport, enable_nearest: bool = False, auto_reload: bool = True):

        self._airport = airport
        self._default_airport = airport
        self._enable_nearest = enable_nearest
        self._gps = None
        self._ui_elements = {}
        
        self._reload_timer = None
        self._auto_reload = auto_reload

        self._user_position = None

        self._build()

    def _build(self):

        with ui.card(align_items="center").classes('mx-auto').style("width:300px"):
            if self._enable_nearest:
                self._gps = Geoloc(high_accuracy=False, timeout=10.0, on_error=self._gps_error)
                ui.toggle(["Home", "Nearest"], value="Home", on_change=self._toggle_mode)

            with ui.row():
                self._ui_elements["weather_code"] = ui.image(OpenMeteo.weather_picture(None)).style("width:60px")
                self._ui_elements["icao_code"] = ui.label("----").classes('text-h4').style("margin-top: 10px;")
                if not self._auto_reload:
                    ui.button(icon="refresh", on_click=self.update).style("margin-top: 10px;")

            self._ui_elements["airport_name"] = ui.label("Unknown").classes('text-h6 text-center')
            self._ui_elements["weather_time"] = ui.label("YYYY-MM-DD HH:MM:SS UTC")
            self._ui_elements["distance"] = ui.label("--- 10 nm from my position")

            with ui.row():
                self._ui_elements["sunrise"] = ui.label(print_hour(None)).style("margin-top: 5px;")
                ui.html("<span class='material-symbols-outlined'>stat_1</span>").style("margin-top: 5px;")
                ui.image("/weather-icons/horizon.svg").style("width:50px")
                ui.html("<span class='material-symbols-outlined'>stat_minus_1</span>").style("margin-top: 5px;")
                self._ui_elements["sunset"] = ui.label(print_hour(None)).style("margin-top: 5px;")

            with ui.row().style("margin: 0; padding: 0;"):
                self._ui_elements["moonrise"] = ui.label(print_hour(None)).style("margin-top: 5px;")
                ui.html("<span class='material-symbols-outlined'>stat_1</span>").style("margin-top: 5px;")
                self._ui_elements["moon_picture"] = ui.image(OpenMeteo.moon_picture(None)).style("width:50px")
                ui.html("<span class='material-symbols-outlined'>stat_minus_1</span>").style("margin-top: 5px;")
                self._ui_elements["moonset"] = ui.label(print_hour(None)).style("margin-top: 5px;")

            self._ui_elements["runway"] = ui.html()

            with ui.grid(columns=2).classes('mx-auto gap-y-2'):

                ui.label("Altitude:")
                self._ui_elements["altitude"] = ui.label("--- ft")

                ui.label("Pressure Altitude:")
                self._ui_elements["press_alt"] = ui.label("--- ft")

                ui.label("Density Altitude:")
                self._ui_elements["dens_alt"] = ui.label("--- ft")

                ui.label("Temperature:")
                self._ui_elements["temp"] = ui.label("-- °C")

                ui.label("Dew point:")
                self._ui_elements["dew_point"] = ui.label("-- °C")

                ui.label("Pressure (QNH):")
                self._ui_elements["qnh"] = ui.label("---- hPa")

                ui.label("Wind:")
                self._ui_elements["wind"] = ui.label("-- kn (---°)")

                ui.label("Wind Gusts:")
                self._ui_elements["wind_gusts"] = ui.label("-- kn")

                self._ui_elements["bestrunway_label"] = ui.label("Best runway:")
                self._ui_elements["bestrunway"] = ui.label("--")

                self._ui_elements["frontwind_label"] = ui.label("Front wind:")
                self._ui_elements["frontwind"] = ui.label("-- kn")

                self._ui_elements["crosswind_label"] = ui.label("Cross wind:")
                self._ui_elements["crosswind"] = ui.label("-- kn")

                ui.label("Cloud cover:")
                self._ui_elements["cloud_cover"] = ui.label("-- %")

                ui.label("Precipitation:")
                self._ui_elements["precipitation"] = ui.label("-- mm")

        self.update()

    async def _gps_error(self, error):
        logger.error(f"GPS Error : {error}")

    async def _toggle_mode(self, event):

        if event.value == "Nearest":
            try:
                self._user_position = await self._gps.get_position()
                self._airport = Airport.nearest(self._user_position, icao_only=True)
            except Exception as e:
                if type(e) == GeolocError:
                    ui.notify(f'Position denied or unavailable : {e.message}', type='negative')
                elif type(e) == TimeoutError:
                    ui.notify('No responce from Position.', type='warning')
                else:
                    ui.notify(f'Unknow Position error : {e}', type='negative')
                event.sender.value = "Home"
                event.sender.update()
                self._airport = self._default_airport
            else:
                ui.notify(f'Position successfully retrieved ({self._user_position})', type='positive')
        else:
            self._airport = self._default_airport

        self.update()

    def _start_timer(self, update_delay):
        if self._auto_reload:
            logger.debug(f"Start reload timer {update_delay:.2f} s")

            if self._reload_timer:
                self._reload_timer.cancel()
                del self._reload_timer

            self._reload_timer = threading.Timer(update_delay, self.update)
            self._reload_timer.start()

    def update(self):
        
        weather = self._airport.current_weather
        is_day = weather['is_day'] != 0
        weather_code = weather['weather_code']
        astro_info = self._airport.current_astro()

        if not weather or not astro_info:
            logger.warning(f"Fail to get weater datas of {self._airport.icao_code}.")
            self._start_timer(10)
            return

        logger.debug(f"Update weather of {self._airport.icao_code} (datas date : {weather['time']})")

        self._ui_elements["weather_code"].source = OpenMeteo.weather_picture(weather_code, is_day)
        self._ui_elements["icao_code"].text = self._airport.icao_code
        self._ui_elements["airport_name"].text = self._airport.name
        self._ui_elements["weather_time"].text = weather['time'].replace("T", " ")+" UTC"

        if not self._user_position is None:
            distance = self._airport.distance_to(self._user_position, unit="nm")
            self._ui_elements["distance"].set_visibility(True)
            self._ui_elements["distance"].text = f"{distance:.2f} nm from my position"
        else:
            self._ui_elements["distance"].set_visibility(False)

        self._ui_elements["sunrise"].text = print_hour(astro_info['sunrise'][0])
        self._ui_elements["sunset"].text = print_hour(astro_info['sunset'][0])
        self._ui_elements["moonrise"].text = print_hour(astro_info['moonrise'][0])
        self._ui_elements["moon_picture"].source = OpenMeteo.moon_picture(astro_info['moon_phase'][0])
        self._ui_elements["moonset"].text = print_hour(astro_info['moonset'][0])

        wind_speed = weather['wind_speed_10m']
        wind_dir = weather['wind_direction_10m']
        runway = self._airport.best_runway(wind_speed, wind_dir)

        if runway:
            self._ui_elements["runway"].set_visibility(True)
            self._ui_elements["runway"].content = runway.trace_runway(
                wind_dir=wind_dir,
                wind_speed=wind_speed,
                south_lat=self._airport.position.latitude < 0
            )
        else:
            self._ui_elements["runway"].set_visibility(False)

        altitude        = self._airport.position.altitude()
        qnh             = weather['pressure_msl']
        press_alt       = pressure_altitude(altitude, qnh)
        temp            = weather['temperature_2m']
        humidity        = weather['relative_humidity_2m']
        dens_alt        = density_altitude(altitude, qnh, temp, humidity)
        dew_point_val   = dew_point(temp, humidity)

        self._ui_elements["altitude"].text = f"{Quantity(altitude, "m").to("ft"):~P.0f}"
        self._ui_elements["press_alt"].text = f"{Quantity(press_alt, "m").to("ft"):~P.0f}"
        self._ui_elements["dens_alt"].text = f"{Quantity(dens_alt, "m").to("ft"):~P.0f}"
        self._ui_elements["temp"].text = f"{temp} °C"
        self._ui_elements["dew_point"].text = f"{dew_point_val:.1f} °C"
        self._ui_elements["qnh"].text = f"{qnh} hPa"
        self._ui_elements["wind"].text = f"{wind_speed:.1f} kn ({wind_dir:.0f}°)"
        self._ui_elements["wind_gusts"].text = f"{weather['wind_gusts_10m']:.1f} kn"
        self._ui_elements["cloud_cover"].text = f"{weather['cloud_cover']} %"
        self._ui_elements["precipitation"].text = f"{weather['precipitation']} mm"

        if runway:
            ident, front_wind, cross_wind = runway.cross_wind(wind_speed, wind_dir)
            self._ui_elements["bestrunway"].text = f"{ident}"
            self._ui_elements["frontwind"].text  = f"{front_wind:.1f} kn"
            self._ui_elements["crosswind"].text  = f"{cross_wind:.1f} kn"
            runway_visibitity = True
        else:
            runway_visibitity = False

        self._ui_elements["bestrunway_label"].set_visibility(runway_visibitity)
        self._ui_elements["frontwind_label"].set_visibility(runway_visibitity)
        self._ui_elements["crosswind_label"].set_visibility(runway_visibitity)

        self._ui_elements["bestrunway"].set_visibility(runway_visibitity)
        self._ui_elements["frontwind"].set_visibility(runway_visibitity)
        self._ui_elements["crosswind"].set_visibility(runway_visibitity)

        date = datetime.datetime.fromisoformat(weather['time']+"Z")
        update_delay = (date.timestamp() + weather['interval']) - time.time()
        self._start_timer(update_delay)