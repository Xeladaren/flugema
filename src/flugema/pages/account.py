import re

from nicegui import ui

from ..datas import User, Airport
from ..utils.password import PasswordChecker

import logging
logger = logging.getLogger(__name__)

def build_account_page():
    ui.page_title("Flugema - Account")

    user = User.from_storage()
    user_data = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "home_airport": user.home_airport,
        "openapi_apikey": user.openapi_apikey
    }

    airports_list = {user.home_airport.id: str(user.home_airport)}

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("User infos").classes('text-h5')
        with ui.row(align_items="center").classes('w-full'):
            ui.input("Username", 
                on_change=lambda e: _str_value_change(e, user_data, "username"),
                value=user_data["username"],
                validation={
                    "Invalid username": lambda value: re.match(r"^[\w]+$", value) != None,
                    "Too short": lambda value: len(value) >= 5,
                    "Username exist": lambda value: value == user.username or not User.username_exist(value)
                }
            ).style("width:300px;")

            ui.input("E-Mail", 
                on_change=lambda e: _str_value_change(e, user_data, "email"),
                value=user_data["email"],
                validation={
                    "Invalid email": lambda value: re.match(r"^((?!\.)[\w\-_.]*[^.])(@\w+)(\.\w+(\.\w+)?[^.\W])$", value) != None,
                    "E-Mail exist": lambda value: value == user.email or not User.email_exist(value)
                }
            ).style("width:300px;")

            ui.input("Full name", 
                on_change=lambda e: _str_value_change(e, user_data, "full_name"),
                value=user_data["full_name"]
            ).style("width:300px;")

            ui.select(  
                label="Home airport",
                value=user_data["home_airport"].id,
                options=airports_list,
                new_value_mode="add",
                with_input=True,
                on_change=lambda e: _home_airport_change(e, user_data),
                key_generator=lambda e: _home_airport_key(e)
            ).style("width:300px;")

        ui.button('Save', 
            icon="save", 
            color="green", 
            on_click=lambda: _update_datas(user_data, user)
        ).classes('mx-auto')

    with ui.card(align_items="center").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Password").classes('text-h5')
        with ui.row(align_items="center").classes('w-full'):
            old_password = ui.input("Old password", 
                password=True,
                password_toggle_button=True
            ).style("width:300px;")
            ui.label("")
            new_password = ui.input("New password", 
                password=True,
                password_toggle_button=True,
                validation={
                    "Too short": lambda value: not value or len(value) >= PasswordChecker.MIN_LENGTH,
                    "Unsafe password": lambda value: not value or PasswordChecker.check(value)
                }
            ).style("width:300px;")
            confirm_password = ui.input("Confirm password", 
                password=True,
                password_toggle_button=True,
                validation={"Password not concord": lambda value: not value or value == new_password.value}
            ).style("width:300px;")
        ui.button('Update', 
            icon="key", 
            color="green", 
            on_click=lambda: _update_password(user, old_password, new_password, confirm_password)
        ).classes('mx-auto')

    with ui.card(align_items="left").style("max-width:650px; width:100%").classes('mx-auto'):
        ui.label("Api keys").classes('text-h5 mx-auto')

        ui.input("OpenAIP", 
            value=user_data["openapi_apikey"],
            password=True,
            password_toggle_button=True,
            on_change=lambda e: _str_value_change(e, user_data, "openapi_apikey"),
        ).style("width:100%;")
        ui.html("<a href='https://www.openaip.net/'>OpenAIP</a> key is needed to have airspace infos in map.").classes('[&_a]:underline')

        ui.button('Save', 
            icon="save", 
            color="green", 
            on_click=lambda: _update_apis(user_data, user)
        ).classes('mx-auto')

def _ckeck_password_safe(password: str) -> bool:
    if len(password) < 10:
        return False
    return True

def _check_value(value, error_msg):
    if not value:
        raise ValueError(error_msg)

def _update_password(user, old, new, confirm):
    try:
        _check_value(old.value, "Old password are required.")
        _check_value(new.value, "New password are required.")
        _check_value(confirm.value, "Confirm password are required.")

        if new.value != confirm.value:
            raise ValueError(f"New passport not concord")

        if not user.set_password(old.value, new.value):
            raise ValueError(f"Invalid password")

    except ValueError as e:
        ui.notify(f"{e}", type="negative")
    except Exception as e:
        ui.notify(f"{e.__class__.__name__}: {e}", type="negative")
        logger.exception("Fail to update password.")
    else:
        ui.notify(f"Password changed", type="positive")
    finally:
        old.value = None
        new.value = None
        confirm.value = None

def _update_datas(user_data, user):
    try:
        user.username       = user_data["username"]
        user.email          = user_data["email"]
        user.full_name      = user_data["full_name"]
        user.home_airport   = user_data["home_airport"] 
    except ValueError as e:
        ui.notify(f"{e}", type="negative")
    except Exception as e:
        ui.notify(f"{e.__class__.__name__}: {e}", type="negative")
        logger.exception("Fail to update User datas.")
    else:
        ui.notify(f"User infos changed", type="positive")

def _update_apis(user_data, user):
    try:
        user.openapi_apikey       = user_data["openapi_apikey"]
    except ValueError as e:
        ui.notify(f"{e}", type="negative")
    except Exception as e:
        ui.notify(f"{e.__class__.__name__}: {e}", type="negative")
        logger.exception("Fail to update APIs.")
    else:
        ui.notify(f"User APIs changed", type="positive")

def _re_validate(value, pattern, error_msg):
    validate = re.match(pattern, value)
    if not validate:
        ui.notify(error_msg, type="negative")

def _str_value_change(event, user_data, key):
    user_data[key] = event.value

def _home_airport_change(event, user_data):
    if event.value:
        airport = Airport.from_id(event.value)

        value = str(airport)
        event.sender.options[event.value] = value
        user_data["home_airport"] = airport

    if None in event.sender.options:
        del event.sender.options[None]

    event.sender.update()

def _home_airport_key(value):
    value = value.upper()
    airport = Airport.from_icao(value)
    if airport:
        return airport.id
    ui.notify(f"Airport {value} not found", type="negative")
    return None


