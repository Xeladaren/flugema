
from nicegui import ui

from ..datas import User

def build_admin_page():

    ui.page_title("Flugema - Admin")
    user = User.from_storage()

    if user.role != "admin":
        ui.navigate.back()
        return None

    ui.label('Page Admin not created').classes('text-h4')