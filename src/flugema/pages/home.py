from nicegui import ui

from ..datas.users import User
from ..datas import Airport, OpenMeteo

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

        if home_airport.runways:
            runway = home_airport.runways[0]
            ui.html(runway.trace_runway(
                wind_dir=home_weather['wind_direction_10m'],
                wind_speed=home_weather['wind_speed_10m'],
                south_lat=home_airport.position.latitude < 0
            ))

        with ui.grid(columns=2).classes('mx-auto'):
            ui.label("Temperature:")
            ui.label(f"{home_weather['temperature_2m']} °C")

            ui.label("Humidity:")
            ui.label(f"{home_weather['relative_humidity_2m']} %")

            ui.label("Pressure (QNH):")
            ui.label(f"{home_weather['pressure_msl']} hPa")

            ui.label("Wind:")
            ui.label(f"{home_weather['wind_speed_10m']} kn ({home_weather['wind_direction_10m']}°)")

            ui.label("Wind Gusts:")
            ui.label(f"{home_weather['wind_gusts_10m']} kn")

            ui.label("Cloud cover:")
            ui.label(f"{home_weather['cloud_cover']} %")

            ui.label("Precipitation:")
            ui.label(f"{home_weather['precipitation']} mm")
        pass