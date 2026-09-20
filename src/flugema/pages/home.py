from nicegui import ui
import pint

from ..datas import User, Flight, Airport, OpenMeteo

from ..utils.weather import dew_point, pressure_altitude, density_altitude
from ..utils.time import print_hour, formated_min
from ..ui.geoloc import Geoloc, GeolocError

from ..ui.widgets import AirportWeatherWidget

ureg = pint.UnitRegistry()
Quantity = ureg.Quantity

def build_home_page():
    ui.page_title("Flugema")
    user = User.from_storage()
    widgets = []
    ui.query('.nicegui-content').classes('p-0 gap-0').style("height: calc(100vh - 90px)")
    with ui.scroll_area().classes('size-full m-0'):
        with ui.row(wrap=False).classes('mx-auto'):
            widgets.append(AirportWeatherWidget(user.home_airport, enable_nearest=True))
            # weather_widget(user)
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
