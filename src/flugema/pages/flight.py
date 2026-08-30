from nicegui import app, ui
import plotly.graph_objects as go
from datetime import datetime

from ..datas.flight import Flight
from ..datas.users import User
from ..utils.geo import GeoPath
from ..utils.time import formated_min

async def build_flight_page(id: int):
    ui.page_title(f"Flugema - Flight {id}")

    user = User.from_storage()
    flight = Flight.from_id(id)

    if flight.user != user:
        ui.navigate.back()
        return None

    with ui.button_group().classes('mx-auto'):

        if preview_flight := flight.preview:
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to(f"/flight/{preview_flight.id}"))
        else:
            ui.button(icon="arrow_back").disable()

        ui.button(icon="table_chart", on_click=lambda: ui.navigate.to("/logbook"))
        ui.button(icon="edit_square", on_click=lambda: ui.navigate.to(f"/flight/edit/{id}"))
        ui.button(icon="delete", color='red', on_click=lambda: delete_flight(flight))

        if next_flight := flight.next:
            ui.button(icon="arrow_forward", on_click=lambda: ui.navigate.to(f"/flight/{next_flight.id}"))
        else:
            ui.button(icon="arrow_forward").disable()


    geo_path = flight.geo_path

    with ui.tabs().classes('w-full') as tabs:
        general = ui.tab('General')
        map = ui.tab('Map')
        altitude = ui.tab('Altitude')

    with ui.tab_panels(tabs, value=general).classes('w-full bg-transparent'):
        with ui.tab_panel(general):
            with ui.card().style("max-width:650px; width:100%").classes('mx-auto'):
                with ui.grid(columns=2):
                    ui.label(f'Airplane :')
                    ui.label(f'{flight.airplane.registration} - {flight.airplane.type}')

                    ui.label(f'Pilot function :')
                    ui.label(f'{Flight.ROLES[flight.role]}')

                    ui.label(f'Pilot-in-command name :')
                    ui.label(f'{flight.pic_name}')

                    ui.label(f'Total time of flight :')
                    ui.label(f'{formated_min(flight.total_min)}')
            
            with ui.card().style("max-width:650px; width:100%").classes('mx-auto'):
                ui.label(f'Remarks').classes('text-h6')
                ui.html(f"<p>{flight.remarks}</p>").classes('w-full')


            columns = [
                {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left', 'style': 'width: 150px'},
                {'name': 'time', 'label': 'Time', 'field': 'time', 'align': 'left'},
            ]
            rows = [
                {'type': 'Day',   'time': formated_min(flight.total_min - flight.night_min - flight.ifr_min)},
                {'type': 'Night', 'time': formated_min(flight.night_min)},
                {'type': 'IFR',   'time': formated_min(flight.ifr_min)}
            ]
            op_table = ui.table(columns=columns, rows=rows, title="Operational condition time").style("max-width:650px; width:100%").classes('mx-auto')
            op_table.props('dense table-header-class=hidden')
            op_table.classes('w-full')

            columns = [
                {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left', 'style': 'width: 150px'},
                {'name': 'time', 'label': 'Time', 'field': 'time', 'align': 'left'},
            ]
            rows = [
                {'type': 'Day',   'time': flight.ldg_day},
                {'type': 'Night', 'time': flight.ldg_night}
            ]
            landing_table = ui.table(columns=columns, rows=rows, title="Landings").style("max-width:650px; width:100%").classes('mx-auto')
            landing_table.props('dense table-header-class=hidden')
            landing_table.classes('w-full')

            with ui.card().style("max-width:650px; width:100%").classes('mx-auto'):
                with ui.timeline(side='right'):

                    ui.timeline_entry(
                        flight.departure.municipality + ", " +
                        flight.departure.region.name  + ", " +
                        flight.departure.country.name + ", " +
                        flight.departure.continent,
                        title=flight.departure.icao_code + " - " + flight.departure.name,
                        subtitle=flight.departure_datetime.isoformat(timespec='minutes', sep=' ').replace("+00:00", " UTC"),
                        icon="flight_takeoff")

                    for touch_and_go in flight.touch_and_go:
                        airport = touch_and_go["airport"]
                        count = touch_and_go["count"]
                        ui.timeline_entry(
                            airport.municipality + ", " +
                            airport.region.name  + ", " +
                            airport.country.name + ", " +
                            airport.continent,
                            title=airport.icao_code + " - " + airport.name,
                            subtitle=f'{count} touch-and-go')

                    ui.timeline_entry(
                        flight.arrival.municipality + ", " +
                        flight.arrival.region.name  + ", " +
                        flight.arrival.country.name + ", " +
                        flight.arrival.continent,
                        title=flight.arrival.icao_code + " - " + flight.arrival.name,
                        subtitle=flight.arrival_datetime.isoformat(timespec='minutes', sep=' ').replace("+00:00", " UTC"),
                        icon='flight_land')

        with ui.tab_panel(altitude).classes('w-full h-full p-0').style('height: calc(100vh - 250px)'):
            y1 = geo_path.altitudes_list(unit="ft")
            y2 = geo_path.ground_altitudes_list(unit="ft")
            x = geo_path.time_list

            if geo_path.time_list:
                fig = {
                    'data': [
                        {
                            'type': 'scatter',
                            'name': 'Altitudes',
                            'x': x,
                            'y': y1,
                            "marker": {
                                "color": 'blue',
                            }
                        }
                    ],
                    'layout': {
                        'margin': {'l': 50, 'r': 0, 't': 50, 'b': 50},
                    },
                }
                if y2:
                    fig['data'].append({
                            'type': 'scatter',
                            'name': 'Ground',
                            'x': x,
                            'y': y2,
                            "marker": {
                                "color": 'green',
                            }
                    })
                ui.plotly(fig).classes('w-full h-full')
            else:
                ui.label("No altitudes Datas")

        with ui.tab_panel(map).classes('w-full h-full p-0').style('height: calc(100vh - 250px)'):
            m = ui.leaflet(center=(47.082100, -0.877064)).classes('w-full h-full')

            # m.clear_layers()
            if user.openapi_apikey:
                m.tile_layer(url_template=fr"https://api.tiles.openaip.net/api/data/openaip/{{z}}/{{x}}/{{y}}.png?apiKey={user.openapi_apikey}")

            m.generic_layer(name='polyline', args=[geo_path.position_list, {'color': '#30AFFF'}])

            m.generic_layer(name='circleMarker', args=[flight.departure.position.raw, {'color': '#059212', "fillOpacity": 0.5, 'radius': 6}])

            for touch_and_go in flight.touch_and_go:
                m.generic_layer(name='circleMarker', args=[touch_and_go["airport"].position.raw, {'color': '#FE7F2D', "fillOpacity": 0.5, 'radius': 6}])

            m.generic_layer(name='circleMarker', args=[flight.arrival.position.raw,  {'color': '#F93827', "fillOpacity": 0.5, 'radius': 6}])

            await m.initialized()
            m.run_map_method('fitBounds', geo_path.get_bounds(), {"padding": [10, 10]})


def delete_flight(flight):
    flight.remove()
    ui.navigate.to("/logbook")
