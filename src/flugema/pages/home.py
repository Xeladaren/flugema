from nicegui import ui

from ..datas.users import User
from ..datas import Airport, OpenMeteo

from ..utils.weather import dew_point


def build_home_page():
    ui.page_title("Flugema")

    user = User.from_storage()

    # ui.label(f'Bienvenue {user.full_name}').classes('text-h4').classes('mx-auto')

    with ui.card(align_items="center").style("width:300px").classes('mx-auto'):
        home_airport = user.home_airport
        home_weather = home_airport.current_weather
        is_day = home_weather['is_day'] != 0
        weather_code = home_weather['weather_code']

        with ui.row():
            ui.image(OpenMeteo.weather_picture(weather_code, is_day)).style("width:60px")
            ui.label(home_airport.icao_code).classes('text-h4').style("margin-top: 10px;")

        ui.label(home_airport.name).classes('text-h6')
        ui.label(home_weather['time'].replace("T", " ")+" UTC")

        wind_speed = home_weather['wind_speed_10m']
        wind_dir = home_weather['wind_direction_10m']
        runway = home_airport.best_runway(wind_speed, wind_dir)
        if runway:
            ident, front_wind, cross_wind = runway.cross_wind(wind_speed, wind_dir)

            ui.html(runway.trace_runway(
                wind_dir=wind_dir,
                wind_speed=wind_speed,
                south_lat=home_airport.position.latitude < 0
            ))

        with ui.grid(columns=2).classes('mx-auto'):
            ui.label("Temperature:")
            ui.label(f"{home_weather['temperature_2m']} °C")

            dew_point_val = dew_point(home_weather['temperature_2m'], home_weather['relative_humidity_2m'])
            ui.label("Dew point:")
            ui.label(f"{dew_point_val:.1f} °C")

            ui.label("Pressure (QNH):")
            ui.label(f"{home_weather['pressure_msl']} hPa")

            ui.label("Wind:")
            ui.label(f"{wind_speed:.1f} kn ({wind_dir:.0f}°)")

            ui.label("Wind Gusts:")
            ui.label(f"{home_weather['wind_gusts_10m']:.1f} kn")
            
            if runway:
                ui.label(f"Best runway:")
                ui.label(f"{ident}")

                ui.label(f"Front wind:")
                ui.label(f"{front_wind:.1f} kn")

                ui.label(f"Cross wind:")
                ui.label(f"{cross_wind:.1f} kn")

            ui.label("Cloud cover:")
            ui.label(f"{home_weather['cloud_cover']} %")

            ui.label("Precipitation:")
            ui.label(f"{home_weather['precipitation']} mm")
        pass