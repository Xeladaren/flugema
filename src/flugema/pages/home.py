from nicegui import ui

from ..datas import User, Flight, Airport, OpenMeteo

from ..utils.weather import dew_point
from ..utils.time import print_hour, formated_min


def build_home_page():
    ui.page_title("Flugema")

    user = User.from_storage()
    ui.query('.nicegui-content').classes('p-0 gap-0').style("height: calc(100vh - 90px)")
    with ui.scroll_area().classes('size-full m-0'):
        with ui.row(wrap=False).classes('mx-auto'):
            home_weather_widget(user)
            flight_stats_widget(user)

def flight_stats_widget(user):
    stats = user.flights_stats()

    with ui.card(align_items="left").classes('mx-auto').style("width:300px"):
        ui.label("Stats").classes('text-h6')
        with ui.grid(columns="auto auto").classes('gap-y-2'):
            ui.label("Total duration:")
            ui.label(formated_min(stats['durations']['total']))

            farthest_airport = stats['farthest-airport']
            ui.label("Farthest airport:")
            ui.label(f"{farthest_airport} ({user.home_airport.distance_to(farthest_airport, unit="nm"):.0f} nm)")

        tree_data = [{
            "id": 0,
            "label": f"Visited airports: {len(stats['airports'])}",
            "children": []
        }]

        for airport in stats['airports']:
            tree_data[0]['children'].append({
                "id": airport.id,
                "label": str(airport)
            })

        ui.tree(tree_data)

        ui.label("Flight contitions").classes('text-h6')
        with ui.grid(columns="140px auto").classes('gap-y-2'):
            ui.label("Day:")
            ui.label(formated_min(stats['durations']['contition']['day']))
        
            ui.label("Night:")
            ui.label(formated_min(stats['durations']['contition']['night']))

            ui.label("IFR:")
            ui.label(formated_min(stats['durations']['contition']['ifr']))

        ui.label("Pilote function").classes('text-h6')
        with ui.grid(columns="140px auto").classes('gap-y-2'):
            for role in stats['durations']['function']:
                ui.label(f"{Flight.ROLES[role]}:")
                ui.label(formated_min(stats['durations']['function'][role]))

        ui.label("Landings").classes('text-h6')
        with ui.grid(columns="140px auto").classes('gap-y-2'):
            ui.label("Day:")
            ui.label(stats['landings']['day'])
        
            ui.label("Night:")
            ui.label(stats['landings']['night'])

            ui.label("IFR Approach:")
            ui.label(stats['apch_ifr'])

def home_weather_widget(user):
    with ui.card(align_items="center").classes('mx-auto').style("width:300px"):
        home_airport = user.home_airport
        home_weather = home_airport.current_weather
        is_day = home_weather['is_day'] != 0
        weather_code = home_weather['weather_code']

        with ui.row():
            ui.image(OpenMeteo.weather_picture(weather_code, is_day)).style("width:60px")
            ui.label(home_airport.icao_code).classes('text-h4').style("margin-top: 10px;")

        ui.label(home_airport.name).classes('text-h6')
        ui.label(home_weather['time'].replace("T", " ")+" UTC")

        astro_info = home_airport.current_astro()
        if astro_info:
            with ui.row():
                ui.label(print_hour(astro_info['sunrise'][0])).style("margin-top: 5px;")
                ui.html("<span class='material-symbols-outlined'>stat_1</span>").style("margin-top: 5px;")
                ui.image("/weather-icons/horizon.svg").style("width:50px")
                ui.html("<span class='material-symbols-outlined'>stat_minus_1</span>").style("margin-top: 5px;")
                ui.label(print_hour(astro_info['sunset'][0])).style("margin-top: 5px;")

            with ui.row().style("margin: 0; padding: 0;"):
                ui.label(print_hour(astro_info['moonrise'][0])).style("margin-top: 5px;")
                ui.html("<span class='material-symbols-outlined'>stat_1</span>").style("margin-top: 5px;")
                ui.image(OpenMeteo.moon_picture(astro_info['moon_phase'][0])).style("width:50px")
                ui.html("<span class='material-symbols-outlined'>stat_minus_1</span>").style("margin-top: 5px;")
                ui.label(print_hour(astro_info['moonset'][0])).style("margin-top: 5px;")

        wind_speed = home_weather['wind_speed_10m']
        wind_dir = home_weather['wind_direction_10m']
        runway = home_airport.best_runway(wind_speed, wind_dir)
        if runway:
            ui.html(runway.trace_runway(
                wind_dir=wind_dir,
                wind_speed=wind_speed,
                south_lat=home_airport.position.latitude < 0
            ))

        with ui.grid(columns=2).classes('mx-auto gap-y-2'):
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
                ident, front_wind, cross_wind = runway.cross_wind(wind_speed, wind_dir)

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