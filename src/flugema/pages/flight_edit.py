from nicegui import ui
import datetime
import io

from ..datas import Airport, User, Flight, Airplane
from ..utils.geo import GeoPath
from ..utils.time import formated_min

import logging
logger = logging.getLogger(__name__)

class AirplaneDataError(ValueError):
    pass

def build_flight_edit_page(id: int | None = None):
    """
    Build page to update or add Flight
    """

    user = User.from_storage()

    if id:
        ui.page_title("Flugema - Edit flight")
        flight = Flight.from_id(id)
        if not flight or flight.user != user:
            ui.navigate.back()
            return None
        else:
            datas = flight.data
    else:
        ui.page_title("Flugema - New flight")
        flight = None

        now = datetime.datetime.now(tz=datetime.UTC)
        now_str = now.replace(tzinfo=None).isoformat(timespec='minutes')

        datas = {
            "id": None, 
            "user": user,
            'departure': user.home_airport, 
            'departure_time': datetime.datetime.now(tz=datetime.UTC), 
            'arrival': user.home_airport, 
            'arrival_time': datetime.datetime.now(tz=datetime.UTC), 
            'airplane': None,
            'role': None,
            'total_min': 132,
            'night_min': 0,
            'ifr_min': 0,
            'ldg_day': 1,
            'ldg_night': 0,
            'apch_ifr': 0,
            'pic_name': None, 
            'remarks': '',
            'page_break': False,
            'geo_path': None,
            'touch_and_go': [],
        }


    airports_list = {user.home_airport.id: str(user.home_airport)}
    update_list = []

    if not datas["departure"].id in airports_list:
        airports_list[datas["departure"].id] = str(datas["departure"])

    if not datas["arrival"].id in airports_list:
        airports_list[datas["arrival"].id] = str(datas["arrival"])

    for touch in datas["touch_and_go"]:
        if not touch["airport"].id in airports_list:
            airports_list[touch["airport"].id] = str(touch["airport"])
    
    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Departure").classes('text-h5')
        with ui.row(align_items="center").classes('w-full'):
            update_list.append(ui.select(  
                label="Place", 
                value=datas["departure"].id,
                options=airports_list, 
                new_value_mode="add", 
                with_input=True, 
                on_change=lambda e: airport_change(e, datas, "departure", update_list),
                key_generator=lambda e: airport_key(e)
            ).style("width:300px;").classes('mx-auto'))
            ui.input("Time", 
                value=datas["departure_time"].replace(tzinfo=None).isoformat(timespec='minutes'),
                on_change=lambda e: datetime_change(e, datas, "departure_time")
            ).props('type="datetime-local"').style("width:300px;").classes('mx-auto')

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Arrival").classes('text-h5')
        with ui.row(align_items="center"):
            update_list.append(ui.select(  
                label="Place", 
                value=datas["arrival"].id,
                options=airports_list, 
                new_value_mode="add", 
                with_input=True, 
                on_change=lambda e: airport_change(e, datas, "arrival", update_list), 
                key_generator=lambda e: airport_key(e)
            ).style("width:300px;").classes('mx-auto'))

            ui.input("Time", 
                value=datas["arrival_time"].replace(tzinfo=None).isoformat(timespec='minutes'),
                on_change=lambda e: datetime_change(e, datas, "arrival_time")
            ).props('type="datetime-local"').style("width:300px;").classes('mx-auto')

    grid_data = {
        'columnDefs': [
            {
                'field': 'airport_id', 
                'hide': True
            },
            {
                'headerName': 'Airport', 
                'field': 'airport', 
                "sortable": False
            },
            {
                'headerName': 'Count', 
                'field': 'count', 
                "sortable": False, 
                'editable': True,
                "width": 80
            },
        ],
        'rowData': [],
        'rowSelection': {'mode': 'multiRow'},
    }
    for touch in datas["touch_and_go"]:
        grid_data["rowData"].append({
            "airport_id": touch["airport"].id,
            "airport": str(touch["airport"]),
            "count": touch["count"]
        })
    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Touch-and-go").classes('text-h5')
        grid = ui.aggrid(grid_data).style("width:100%;").on('cellValueChanged', lambda event: touch_update_count(event, datas, touch_select, grid))
        with ui.row(align_items="center").style("width:100%;  max-width:400px;"):
            touch_select = ui.select(  
                label="Touch-and-go",
                value=user.home_airport.id,
                options=airports_list, 
                new_value_mode="add", 
                with_input=True, 
                on_change=lambda e: airport_change(e, None, None, update_list),
                key_generator=lambda e: airport_key(e)
            ).style("width:50%; max-width:300px;").classes('mx-auto')
            update_list.append(touch_select)

            with ui.button_group().classes('mx-auto'):
                ui.button(icon="add", on_click=lambda: touch_add(datas, touch_select, grid))
                ui.button(icon="delete", color='red', on_click=lambda: touch_rm(datas, touch_select, grid))
    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Flight contitions").classes('text-h5')
        with ui.row(align_items="center"):
            ui.input("Night", 
                on_change=lambda e: duration_change(e, datas, "night_min"),
                value=formated_min(datas["night_min"]) if datas["night_min"] > 0 else None
            ).props('type="time"').style("width:300px;")

            ui.input("IFR", 
                on_change=lambda e: duration_change(e, datas, "ifr_min"),
                value=formated_min(datas["ifr_min"]) if datas["ifr_min"] > 0 else None
            ).props('type="time"').style("width:300px;")

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Landings").classes('text-h5')
        with ui.row(align_items="center"):
            ui.input("Night landings", 
                on_change=lambda e: integer_chage(e, datas, "ldg_night"),
                value=datas["ldg_night"]
            ).props('type="number"').style("width:300px;")

            ui.input("IFR Approach",
                on_change=lambda e: integer_chage(e, datas, "apch_ifr"),
                value=datas["apch_ifr"]
            ).props('type="number"').style("width:300px;")

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Pilot").classes('text-h5')
        with ui.row(align_items="center"):
            pic_name = ui.input("Pilot-In-Command Name", 
                on_change=lambda e: value_chage(e, datas, "pic_name"),
                value=datas["pic_name"] if "pic_name" in datas else None
            ).style("width:300px;")

            if datas["role"] == "pic":
                pic_name.disable()

            ui.select(  
                label="Function",
                value=datas["role"],
                options=Flight.ROLES, 
                on_change=lambda e: role_chage(e, datas, pic_name)
            ).style("width:300px;")

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Airplane").classes('text-h5')
        with ui.row(align_items="center"):
            airplane_type = ui.input("Airplane type",
                value=datas["airplane"].type if datas["airplane"] else None,
                on_change=lambda e: value_chage(e, datas, "airplane_type")
            ).style("width:300px;")

            if datas["airplane"]:
                airplane_type.disable()
                datas["airplane_type"] = datas["airplane"].type
                datas["airplane_reg"]  = datas["airplane"].registration

            airplane_options = []
            for airplane in Airplane.all():
                airplane_options.append(airplane.registration)

            ui.select(  
                label="Airplace reg",
                value=datas["airplane"].registration if datas["airplane"] else None,
                options=airplane_options, 
                new_value_mode="add", 
                with_input=True, 
                on_change=lambda e: airplane_change(e, datas, airplane_type)
            ).style("width:300px;")

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Remarks").classes('text-h5')
        ui.editor(
            value=datas["remarks"],
            on_change=lambda e: value_chage(e, datas, "remarks")
        ).style("width:100%")

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Flight GPS log").classes('text-h5')
        ui.upload(
            on_upload=lambda e: file_uploaded(e, datas),
            max_files=1, 
            auto_upload=True,
            multiple=False
        ).style("width:100%")

    ui.switch('Page break',
        value=datas["page_break"],
        on_change=lambda e: value_chage(e, datas, "page_break")
    ).classes('mx-auto')

    with ui.button_group().classes('mx-auto'):
        ui.button('Save', icon="save", color="green", on_click=lambda: validate_datas(datas, flight))
        ui.button('Cancel', icon="exit_to_app", color="orange", on_click=lambda: cancel(datas))

def check_data(datas, key, error_msg):
    if not key in datas or not datas[key]:
        raise AirplaneDataError(error_msg)

def cancel(datas):
    if "geo_path_file" in datas:
        del datas["geo_path_file"]
    ui.navigate.back()

def validate_datas(datas: dict, flight: Flight | None = None):

    try:
        check_data(datas, "departure",      "Departure are required.")
        check_data(datas, "departure_time", "Departure Time are required.")
        check_data(datas, "arrival",        "Arrival are required.")
        check_data(datas, "arrival_time",   "Arrival Time are required.")
        check_data(datas, "role",           "The Filght Role are required.")
        check_data(datas, "airplane_reg",   "The Airplane registration are required.")
        check_data(datas, "pic_name",       "The Pilot-In-Command name are required.")

        total_duration = datas["arrival_time"] - datas["departure_time"]
        datas["total_min"] = int(total_duration.total_seconds() / 60)

        datas["ldg_day"] = 1 

        for touch in datas["touch_and_go"]:
            datas["ldg_day"] += touch["count"]
        
        datas["ldg_day"] -= datas["ldg_night"]

        if datas["ldg_night"] > 0 and datas["night_min"] == 0:
            raise AirplaneDataError("Night landing need night flight time.")

        if datas["apch_ifr"] > 0 and datas["ifr_min"] == 0:
            raise AirplaneDataError("IFR landing need IFR flight time.")

        if datas["ldg_day"] < 0:
            raise AirplaneDataError("Night landing count can't be more than total landing.")

        if datas["apch_ifr"] > datas["ldg_day"] + datas["ldg_night"]:
            raise AirplaneDataError("IFR approach count can't be more than total landing.")

        if datas["total_min"] <= 0:
            raise AirplaneDataError("Arrival need to be after departure.")

        if datas["arrival_time"] > datetime.datetime.now(tz=datetime.UTC):
            raise AirplaneDataError("Flight can't be on the future.")

        if "night_min" in datas and datas["night_min"] > datas["total_min"]:
            raise AirplaneDataError("Night time can't be more than total time.")

        if "ifr_min" in datas and datas["ifr_min"] > datas["total_min"]:
            raise AirplaneDataError("IFR time can't be more than total time.")

        datas["airplane"] = Airplane.from_reg(datas["airplane_reg"])
        if not datas["airplane"]:
            check_data(datas, "airplane_type",   "The Airplane type are required for new planes.")
            datas["airplane"] = Airplane.new(datas["airplane_reg"], datas["airplane_type"])

        if "geo_path_file" in datas and type(datas["geo_path_file"]) == GeoPath:
            datas["geo_path"] = datas["geo_path_file"].to_storage()
            del datas["geo_path_file"]

        del datas["airplane_type"]
        del datas["airplane_reg"]

        if not datas["id"]:
            flight = Flight.new(datas)
        else:
            flight.update()

        ui.navigate.to(f"/flight/{flight.id}")

    except AirplaneDataError as e:
        ui.notify(f"{e}", type="negative")
    except Exception as e:
        ui.notify(f"{e.__class__.__name__}: {e}", type="negative")
        logger.exception("Flight edit data error.")

async def file_uploaded(elem, datas):

    try:
        str_data = await elem.file.text()
        gpx_file = io.StringIO(str_data)
        geo_path = GeoPath.from_gpx(gpx_file)
        datas["geo_path_file"] = geo_path
    except Exception as e:
        ui.notify(f"Invalid GPX file type: {elem.file.name}", type="negative")
        logger.error(f"Invalid GPX file type: {elem.file.name}, {elem.file.content_type}.")
        elem.sender.reset()

def value_chage(elem, datas, key):
    if elem.value:
        datas[key] = elem.value
    else:
        del datas[key]

def role_chage(elem, datas, pic_name):
    if elem.value == "pic":
        pic_name.value = datas["user"].full_name
        pic_name.disable()
        datas["pic_name"] = datas["user"].full_name
    else:
        pic_name.enable()

    datas["role"] = elem.value


def integer_chage(elem, datas, key):
    if elem.value:
        datas[key] = int(elem.value)

def duration_change(elem, datas, key):
    if elem.value:
        value = elem.value.split(":")
        value = int(value[0]) * 60 + int(value[1])
        datas[key] = value

def datetime_change(elem, datas, key):
    if elem.value:
        date = datetime.datetime.fromisoformat(elem.value+"Z")
        datas[key] = date

def airplane_change(event, datas, airplane_type):
    if event.value:
        airplane_reg = event.value.upper()
        if event.value != airplane_reg:
            event.sender.options.remove(event.value)
            event.sender.options.append(airplane_reg)
            event.sender.value = airplane_reg
        airplane = Airplane.from_reg(airplane_reg)
        if airplane:
            airplane_type.value = airplane.type
            airplane_type.disable()
        else:
            airplane_type.enable()
        
        datas["airplane_reg"] = airplane_reg

def touch_add(datas, touch_select, grid):
    if touch_select.value:
        airport = Airport.from_id(touch_select.value)
        new_row = {
            "airport_id": airport.id,
            "airport": str(airport),
            "count": 1
        }
        grid.options['rowData'].append(new_row)
        datas["touch_and_go"].append({
            "airport": airport,
            "count": 1
        })

def touch_update_count(event, datas, touch_select, grid):
    for row in grid.options['rowData']:
        if event.args["data"]["airport_id"] == row["airport_id"]:
            row["count"] = event.args["data"]["count"]
            break
    
    for touch in datas["touch_and_go"]:
        if touch["airport"].id == event.args["data"]["airport_id"]:
            touch["count"] = event.args["data"]["count"]
            break

async def touch_rm(datas, touch_select, grid):
    selected_list = await grid.get_selected_rows()
    for selected in selected_list:
        grid.options['rowData'].remove(selected)

        for index in range(len(datas["touch_and_go"])):
            if datas["touch_and_go"][index]["airport"].id == selected['airport_id']:
                datas["touch_and_go"].pop(index)
                break

def airport_key(value):
    value = value.upper()
    airport = Airport.from_icao(value)
    if airport:
        return airport.id
    ui.notify(f"Airport {value} not found", type="negative")
    return None

def airport_change(elem, datas, key, update_list):
    if elem.value:
        airport = Airport.from_id(elem.value)

        value = str(airport)
        elem.sender.options[elem.value] = value
        if datas:
            datas[key] = airport

    if None in elem.sender.options:
        del elem.sender.options[None]

    for elem in update_list:
        elem.update()
