import requests
import supervisely as sly

from supervisely.app.widgets import (
    Input,
    Card,
    Button,
    Container,
    Text,
    Flexbox,
)

import src.globals as g

# Input widget for the API key, characters will be hidden.
key_input = Input(type="password")

# Flexbox for all buttons.
check_key_button = Button("Check connection")
change_instance_button = Button(
    "Change instance", icon="zmdi zmdi-swap-vertical-circle"
)
change_instance_button.hide()
buttons_flexbox = Flexbox([check_key_button, change_instance_button])

# Message which is shown if the API key was loaded from the team files.
file_loaded_info = Text(
    text="The API key was loaded from the team files.", status="info"
)
file_loaded_info.hide()

# Message which is shown after the connection check.
check_result = Text()
check_result.hide()

# Main card with all keys widgets.
card = Card(
    "*️⃣ Connect to Assets",
    "Enter the API key and press the button to connect to the Assets API.",
    content=Container(
        widgets=[
            key_input,
            buttons_flexbox,
            file_loaded_info,
            check_result,
        ],
        direction="vertical",
    ),
    collapsable=True,
)
card.collapse()
card.hide()


@check_key_button.click
def connect_to_assets():
    """Checks the connection to the assets instance with specified API key."""
    check_result.hide()

    if not g.STATE.assets_api_key:
        # Reading the API key from the input widget, if it was not loaded from the team files.
        g.STATE.assets_api_key = key_input.get_value()

    try:
        g.STATE.assets_api = sly.Api(
            server_address=g.STATE.instance,
            token=g.STATE.assets_api_key,
            ignore_task_id=True,
        )
        g.STATE.assets_api.team.get_info_by_name(g.DEFAULT_TEAM_NAME)
        sly.logger.info("The connection to the Assets API was successful.")

    except (ValueError, requests.exceptions.HTTPError):
        g.STATE.assets_api_key = None
        sly.logger.warning("The connection to the Assets API failed.")
        check_result.text = "The connection to the Assets API failed, check the key."
        check_result.status = "error"
        check_result.show()
        return

    if g.STATE.from_team_files:
        # If the app was started from the team files, making changes in the GUI state.
        key_input.set_value(g.STATE.assets_api_key)
        change_instance_button.hide()
        key_input.disable()
    else:
        change_instance_button.show()

    check_result.text = f"Successfully connected to: {g.STATE.instance}"
    check_result.status = "success"
    check_result.show()

    # Disabling fields for entering API key if the connection was successful.
    key_input.disable()
    check_key_button.hide()


@change_instance_button.click
def change_instance():
    """Handles the change instance button click event."""
    key_input.enable()
    check_key_button.show()
    change_instance_button.hide()


g.key_from_file()
# Trying to load the API key and instance address from the team files.
if g.STATE.assets_api_key:
    g.STATE.from_team_files = True
    connect_to_assets()
    file_loaded_info.show()
