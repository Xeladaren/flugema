from nicegui import ui

from ..datas.users import User

def build_home_page():
    ui.page_title("Flugema")

    user = User.from_storage()

    ui.label(f'Bienvenue {user.full_name}').classes('text-h4')