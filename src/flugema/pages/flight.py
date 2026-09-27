import os
from nicegui import app, ui
import plotly.graph_objects as go
from datetime import datetime
from functools import partial

from ..datas.flight import Flight
from ..datas.users import User
from ..utils.geo import GeoPath
from ..utils.time import formated_min
from ..datas import Picture

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
        general_tab = ui.tab('General')
        map_tab = ui.tab('Map')
        altitude_tab = ui.tab('Altitude')
        photos_tab = ui.tab('Photos')

    
    with ui.tab_panels(tabs, value=general_tab).classes('w-full bg-transparent'):
        with ui.tab_panel(general_tab):
            tabpanel_general(user, flight)
        with ui.tab_panel(map_tab).classes('w-full h-full p-0').style('height: calc(100vh - 250px)'):
            tabpanel_map(user, flight, geo_path)
        with ui.tab_panel(altitude_tab).classes('w-full h-full p-0').style('height: calc(100vh - 250px)'):
            tabpanel_altitude(user, flight, geo_path)
        with ui.tab_panel(photos_tab).classes('w-full h-full p-0').style('height: calc(100vh - 250px)'):
            tabpanel_photos(flight)

def tabpanel_general(user, flight):

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

def material_icon(name: str, color: str = '#444444', size: int = 20) -> str:
    """Retourne l'expression JS d'un L.divIcon affichant une icône Material."""
    return (
        'L.divIcon({'
        f'html: \'<i class="material-icons" style="font-size:{size}px;'
        f'line-height:{size}px;color:{color};">'
        f'{name}</i>\','
        "className: '',"                      # supprime le cadre blanc par défaut
        f'iconSize: [{size}, {size}],'
        f'iconAnchor: [{size // 2}, {size}],'  # la pointe = bas-centre
        f'popupAnchor: [0, -{size}]'
        '})'
    )

def tabpanel_map(user, flight, geo_path):

    m = ui.leaflet().classes('w-full h-full')

    # m.clear_layers()
    if user.openapi_apikey:
        m.tile_layer(
            url_template=fr"https://api.tiles.openaip.net/api/data/openaip/{{z}}/{{x}}/{{y}}.png?apiKey={user.openapi_apikey}",
            options={"attribution": "<a href='https://www.openaip.net/'>OpenAIP</a>"}
        )

    m.generic_layer(name='polyline', args=[geo_path.position_list, {'color': '#30AFFF'}])

    m.generic_layer(name='circleMarker', args=[flight.departure.position.raw, {'color': '#059212', "fillOpacity": 0.5, 'radius': 6}])

    for touch_and_go in flight.touch_and_go:
        m.generic_layer(name='circleMarker', args=[touch_and_go["airport"].position.raw, {'color': '#FE7F2D', "fillOpacity": 0.5, 'radius': 6}])

    marker_list = []

    def rm_image(picture, dialog, marker):
        picture.remove()
        m.remove_layer(marker)
        dialog.close()

    def dl_image(picture):
        ui.download.file(picture.path, picture.file_name)

    for picture in flight.pictures:
        if picture.position:
            marker = m.marker(latlng=(picture.position.latitude, picture.position.longitude), options={'id': picture.id})
            with ui.dialog().props('maximized') as dialog, ui.card().classes('w-full h-full flex items-center justify-center'):
                ui.image(picture.url).classes('max-h-full')
                ui.button(icon="close", on_click=dialog.close).classes('absolute right-4 top-4').props('flat color=white').classes('bg-black/25')
                with ui.button_group().classes('absolute top-4').props('flat').classes('bg-black/25'):
                    ui.button(icon="download", on_click=partial(dl_image, picture)).props('flat color=white')
                    ui.button(icon="delete", on_click=partial(rm_image, picture, dialog, marker)).props('flat color=red')
            marker_list.append((picture.id, marker, dialog))

    m.generic_layer(name='circleMarker', args=[flight.arrival.position.raw,  {'color': '#F93827', "fillOpacity": 0.5, 'radius': 6}])

    def on_initialized():
        m.run_map_method('fitBounds', geo_path.get_bounds(), {"padding": [10, 10]})
        for id, marker, dialog in marker_list:
            marker.run_method(':setIcon', material_icon('photo_camera'))
            marker.run_method(
                ':on',
                '"click"',
                f'(e) => emitEvent("pic_marker_click", {{id: e.target.options.id}})',
            )

    def on_marker_click(event):
        for id, marker, dialog in marker_list:
            if event.args['id'] == id:
                dialog.open()
                break

    ui.on('pic_marker_click', on_marker_click)
    m.on("init", on_initialized)

def tabpanel_altitude(user, flight, geo_path):

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
                        "color": '#0077FF',
                    }
                }
            ],
            'layout': {
                'margin': {'l': 30, 'r': 10, 't': 40, 'b': 30},
                'xaxis': {},
                'yaxis': {},
                'showlegend': False,
            },
        }
        if y2:
            fig['data'].append({
                    'type': 'scatter',
                    'name': 'Ground',
                    'x': x,
                    'y': y2,
                    "marker": {
                        "color": '#00BB00',
                    }
            })
        
        if app.storage.user.get("dark_mode", False):
            fig["layout"]["paper_bgcolor"] = "#121212"
            fig["layout"]["plot_bgcolor"]  = "#121212"
            fig["layout"]["xaxis"]["color"]  = "#BBBBBB"
            fig["layout"]["yaxis"]["color"]  = "#BBBBBB"
            fig["layout"]["xaxis"]["gridcolor"]  = "#555555"
            fig["layout"]["yaxis"]["gridcolor"]  = "#555555"


        ui.plotly(fig).classes('w-full h-full')
    else:
        ui.label("No altitudes Datas")

def tabpanel_photos(flight):

    images = []

    async def add_images(event):
        nonlocal images

        for image in event.files:
            new_path = Picture.new_path(file_type=image.content_type)
            await image.save(new_path)
            Picture.add(flight, new_path)
        gallery.refresh()

    def rm_image(picture):
        picture.remove()
        gallery.refresh()

    def dl_image(picture):
        ui.download.file(picture.path, picture.file_name)

    @ui.refreshable    
    def gallery():
        with ui.carousel(animated=True, arrows=True, navigation=True).classes('w-full h-full items-center justify-center'):
            for picture in flight.pictures:
                with ui.carousel_slide().classes('p-0 h-full flex items-center justify-center bg-black'):
                    ui.image(picture.url).props('fit=contain').classes('w-full h-full')
                    with ui.button_group().classes('absolute top-4').props('flat').classes('bg-black/25'):
                        ui.button(icon="download", on_click=partial(dl_image, picture)).props('flat color=white')
                        ui.button(icon="delete", on_click=partial(rm_image, picture)).props('flat color=red')
            with ui.carousel_slide(name='add').classes('p-0 h-full flex items-center justify-center bg-black'):
                ui.label("New Photos").classes("text-h4")
                ui.upload(on_multi_upload=add_images, multiple=True).classes('w-4/5 h-full')

    with ui.element('div').classes('relative w-full h-full'):
        gallery()

def delete_flight(flight):
    flight.remove()
    ui.navigate.to("/logbook")
