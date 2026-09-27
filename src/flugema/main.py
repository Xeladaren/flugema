from nicegui import app, ui
import csv
import datetime
import zoneinfo
import os
import json
import hashlib
import secrets
import logging

from fastapi import HTTPException
from fastapi.responses import FileResponse

from . import pages

from .datas.airport import update_all as update_all_airports
from .datas.users import User
from .datas.picture import Picture
from .datas import install_database

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

def check_credentials(username: str, password: str):
    """Vérifie les credentials et redirige si valides"""

    user = User.login(username, password)
    if user:
        app.storage.user.update({'authenticated': True, "user_id": user.id})
        ui.notify(f'Bienvenue {user.full_name}', type='positive')
        ui.navigate.to(app.storage.client.get("redirect_page", "/"))
    else:
        ui.notify('Identifiants invalides', type='negative')

def disconnect():
    app.storage.user.clear()
    ui.navigate.to('/login')

def switch_dark(click_event, dark_mode):

    if not app.storage.user.get("dark_mode", False):
        dark_mode.enable()
        click_event.sender.icon = "dark_mode"
        app.storage.user["dark_mode"] = True
    else:
        dark_mode.disable()
        click_event.sender.icon = "light_mode"
        app.storage.user["dark_mode"] = False

def global_configs(is_auth=False):

    # Set initial Dark mode
    dark_mode  = ui.dark_mode()

    if app.storage.user.get("dark_mode", False):
        dark_mode.enable()
        mode_icon = "dark_mode"
    else:
        dark_mode.disable()
        mode_icon = "light_mode"

    # Build page menues
    with ui.header().classes(replace='row items-center') as header:
        if is_auth:
            ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')

        utc_hour = ui.label()
        ui.timer(1.0, lambda: utc_hour.set_text(
            f"{datetime.datetime.now(tz=datetime.UTC):%X} UTC"
        ))
        
        ui.space()
        ui.button(on_click=lambda e: switch_dark(e, dark_mode), icon=mode_icon).props('flat color=white')

        if is_auth:
            ui.button(on_click=lambda: ui.navigate.to("/account"), icon='account_circle').props('flat color=white')
            ui.button(on_click=lambda: disconnect(), icon='logout').props('flat color=white')

    with ui.footer(value=True) as footer:
        ui.html('''
            &copy; 2026 Flugema - 
            Licence <a href="https://www.gnu.org/licenses/gpl-3.0.fr.html">GPL v3.0</a> - 
            <a href="https://github.com/Xeladaren/flugema">Sources</a>
        ''', sanitize=False).classes('[&_a]:underline')

    if is_auth:

        user = User.from_storage()

        with ui.left_drawer(value=False).classes('bg-blue-100') as left_drawer:
            ui.button("Home", on_click=lambda e: ui.navigate.to("/")).props('flat color=black')
            ui.button("Logbook", on_click=lambda e: ui.navigate.to("/logbook")).props('flat color=black')
            if user.role == "admin":
                ui.button("Admin", on_click=lambda e: ui.navigate.to("/admin")).props('flat color=black')

def check_auth():
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return False
    else:
        return True

@ui.page("/login")
def login():
    """Page de login indépendante du système de sous-pages"""

    global_configs(is_auth=False)

    with ui.card().classes('absolute-center'):
        
        username = ui.input('User or e-mail')
        password = ui.input('Password', password=True, password_toggle_button=True)
        ui.button('Conection', on_click=lambda: check_credentials(username.value, password.value))

@ui.page("/")
def home():
    if check_auth():
        global_configs(is_auth=True)
        pages.build_home_page()

@ui.page("/admin")
def account():
    if check_auth():
        global_configs(is_auth=True)
        pages.build_admin_page()

@ui.page("/account")
def account():
    if check_auth():
        global_configs(is_auth=True)
        pages.build_account_page()

@ui.page("/logbook")
def logbook():
    if check_auth():
        global_configs(is_auth=True)
        pages.build_logbook_page()


@ui.page("/flight/new")
def flight_new():
    if check_auth():
        global_configs(is_auth=True)
        pages.build_flight_edit_page()

@ui.page("/flight/edit/{id}")
def flight_edit(id: int):
    if check_auth():
        global_configs(is_auth=True)
        pages.build_flight_edit_page(id)

@ui.page("/flight/{id}")
async def page_flight_id(id: int):
    if check_auth():
        global_configs(is_auth=True)
        await pages.build_flight_page(id)

@app.get('/picture/{id}')
def get_picture(id: int):
    if app.storage.user.get('authenticated', False):
        picture = Picture.from_id(id)
        user = User.from_storage()
        if picture:
            if picture.flight.user == user:
                return FileResponse(picture.path)
            else:
                raise HTTPException(401)
        else:
            raise HTTPException(404)
    else:
        raise HTTPException(401)


def get_secret_key() -> str:
    """Return FLUGEMA_SECRET_KEY, or generate one and persist it in DATA_DIR."""
    key = os.environ.get("FLUGEMA_SECRET_KEY", "").strip()
    if key:
        return key
    return secrets.token_urlsafe(48)

def main() -> None:

    update_all_airports()
    install_database()
    logger.info("All Databases created!")

    assets_dir = os.path.join(os.path.dirname(__file__), "assets")

    app.add_static_file(url_path="/manifest.json", local_file=os.path.join(assets_dir,  "manifest.json"))
    app.add_static_files(url_path="/icons", local_directory=os.path.join(assets_dir, "icons"))
    app.add_static_files(url_path="/weather-icons", local_directory=os.path.join(assets_dir, "weather-icons"))

    ui.add_head_html('<meta name="description" content="A Flight tool for private pilots.">', shared=True)

    ui.add_head_html('<meta name="og:title" content="Flugema">', shared=True)
    ui.add_head_html('<meta name="og:description" content="A Flight tool for private pilots.">', shared=True)
    ui.add_head_html('<meta name="og:image" content="/icons/icon.svg">', shared=True)

    ui.add_head_html('<link rel="manifest" href="/manifest.json" />', shared=True)

    HOST       = os.environ.get("FLUGEMA_HOST", "127.0.0.1")
    PORT       = int(os.environ.get("FLUGEMA_PORT", 8080))
    ALLOW_IPS  = os.environ.get('FLUGEMA_ALLOW_IPS', '127.0.0.1')
    SECRET_KEY = get_secret_key()

    try:
        logger.info(f"Server started on {HOST}:{PORT} (Proxy allowed ips:{ALLOW_IPS})")
        ui.run(
            storage_secret=SECRET_KEY, 
            reload=False, 
            show=False, 
            title="Flugema", 
            port=PORT,
            host=HOST,
            proxy_headers=True,
            forwarded_allow_ips=ALLOW_IPS,
            show_welcome_message=False,
            favicon=os.path.join(assets_dir, "icons", "favicon.ico")
        )
    except KeyboardInterrupt:
        logger.info("Exit App.")
        os._exit(0)

if __name__ in {"__main__", "__mp_main__"}:
    main()
