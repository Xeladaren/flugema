from nicegui import app, ui

from ..datas.flight import Flight
from ..datas.users  import User

def build_logbook_page():
    ui.page_title("Flugema - Logbook")

    user = User.from_storage()
    
    ui.add_css(
        """
        .sticky-header-table {
            /* Hauteur adaptative à l'écran (moins la barre de titre et marge) */
            height: calc(100vh - 200px);
            max-height: calc(100vh - 200px);
            display: flex;
            flex-direction: column;
        }

        .sticky-header-table .nicegui-table {
            flex: 1;
            overflow: auto;
        }

        .sticky-header-table thead {
            position: sticky;
            top: 0;
            z-index: 10;
            background-color: #5898d4;
        }

        /* Style pour les cellules du header */
        .sticky-header-table th {
            background-color: #5898d4 !important;
        }
        """
    )

    columns = [
        {"name": "date",            'field': 'date',            "label": "Date", 'sortable': True},
        {"name": "departure",       'field': 'departure',       "label": "Departure Place"},
        {"name": "departure_time",  'field': 'departure_time',  "label": "Departure Time"},
        {"name": "arrival",         'field': 'arrival',         "label": "Arrival Place"},
        {"name": "arrival_time",    'field': 'arrival_time',    "label": "Arrival Time"},
        {"name": "type",            'field': 'type',            "label": "Aircraft type"},
        {"name": "registration",    'field': 'registration',    "label": "Aircraft reg"},
        {"name": "pic_name",        'field': 'pic_name',        "label": "PIC Name"},
        {"name": "role",            'field': 'role',            "label": "Role"},
        {"name": "total_min",       'field': 'total_min',       "label": "Total time"},
        {"name": "night_min",       'field': 'night_min',       "label": "Night time"},
        {"name": "ifr_min",         'field': 'ifr_min',         "label": "IFR time"},
        {"name": "ldg_day",         'field': 'ldg_day',         "label": "Day landing"},
        {"name": "ldg_night",       'field': 'ldg_night',       "label": "Night landing"},
        {"name": "apch_ifr",        'field': 'apch_ifr',        "label": "IFR Approach"},
    ]

    flights = [flight.formated_datas() for flight in user.flights]

    # with ui.card().classes('w-full h-full'):
    ui.table(columns=columns, rows=flights, row_key='id', pagination=0).classes('w-full sticky-header-table').on("row-click", lambda row: ui.navigate.to(f'/flight/{row.args[1]["id"]}'))

    with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
        ui.button(on_click=lambda: ui.navigate.to("/flight/new"), icon='add').props('fab')
