import os
import requests

import supervisely as sly
from supervisely.app.widgets import (
    Card,
    SelectProject,
    Button,
    Container,
    ProjectThumbnail,
    Text,
    Tabs,
    Input,
    Flexbox,
    Field,
    Progress,
)

import src.globals as g
import src.ui.settings as settings

select_project = SelectProject(workspace_id=g.STATE.selected_workspace)

project_thumbnail = ProjectThumbnail()
project_thumbnail.hide()

load_button = Button("Load data")
change_project_button = Button("Change project", icon="zmdi zmdi-lock-open")
change_project_button.hide()

no_project_message = Text(
    "Please, select a project before clicking the button.",
    status="warning",
)
no_project_message.hide()

# Input widget for the API key, characters will be hidden.
key_input = Input(type="password")
key_field = Field(
    key_input, "API key", "Enter API key for Assets and check the connection."
)

# Flexbox for all buttons.
check_key_button = Button("Check connection")
change_key_button = Button("Change key", icon="zmdi zmdi-swap-vertical-circle")
change_key_button.hide()
buttons_flexbox = Flexbox([check_key_button, change_key_button])

# Message which is shown if the API key was loaded from the team files.
file_loaded_info = Text(
    text="The API key was loaded from the team files.", status="info"
)
file_loaded_info.hide()

loading_progress = Progress()
loading_progress.hide()

# Message which is shown after the connection check.
check_result = Text()
check_result.hide()

assets_tab_container = Container(
    [key_field, buttons_flexbox, file_loaded_info, check_result, loading_progress]
)

project_tab_container = Container(
    [
        select_project,
        load_button,
        change_project_button,
        project_thumbnail,
        no_project_message,
    ]
)

input_tabs = Tabs(["Project", "Assets"], [project_tab_container, assets_tab_container])

# Input card with all widgets.
card = Card(
    "1️⃣ Input data",
    "Select to load images from an existing project or from the assets primitives.",
    content=input_tabs,
    collapsable=True,
)


@load_button.click
def load_project():
    """Handles the load button click event. Reading values from the SelectProject widget,
    calling the API to get project, workspace and team ids (if they're not set),
    building the table with images and unlocking the rotator and output cards.
    """

    if g.STATE.selected_project:
        project_id = g.STATE.selected_project
        select_project.hide()
        change_project_button.hide()

        sly.logger.info(f"The app was launched from the project with ID: {project_id}.")
    else:
        # Reading the project id from SelectProject widget.
        project_id = select_project.get_selected_id()

        if not project_id:
            # If the project id is empty, showing the warning message.
            no_project_message.show()
            return

        # Changing the values of the global variables to access them from other modules.
        g.STATE.selected_project = project_id
        change_project_button.show()

    no_project_message.hide()

    # Cleaning the static directory when the new project is selected.
    clean_static_dir()

    select_project.disable()
    load_button.hide()

    sly.logger.debug(
        f"Calling API with Project ID {project_id} to get workspace and team IDs."
    )

    g.STATE.selected_workspace = g.api.project.get_info_by_id(
        g.STATE.selected_project
    ).workspace_id
    g.STATE.selected_team = g.api.workspace.get_info_by_id(
        g.STATE.selected_workspace
    ).team_id

    sly.logger.debug(
        f"Recived IDs from the API. Selected team: {g.STATE.selected_team}, "
        f"selected workspace: {g.STATE.selected_workspace}, selected project: {g.STATE.selected_project}"
    )
    project_info = g.api.project.get_info_by_id(g.STATE.selected_project)

    project_thumbnail.set(project_info)
    project_thumbnail.show()

    input_tabs.disable()
    g.STATE.get_project_meta()

    load_data()


def load_data():
    sly.logger.debug("Starting to prepare the data for the app.")

    if g.STATE.assets_api:
        check_key_button.text = "Loading data..."

        sly.logger.info(
            "The app is working with the Assets primitives with provided API key."
        )
        settings.classes_table.hide()
        read_assets()

        loading_progress.show()

        with loading_progress(
            message="Loading assets categories...", total=len(g.STATE.ASSETS.data)
        ) as pbar:
            settings.load_assets(pbar)

        check_key_button.text = "Check connection"

    else:
        sly.logger.info("The app is working with the Supervisely project.")

        settings.classes_table.read_meta(g.STATE.project_meta)
        settings.classes_table.show()
        settings.classes_collapse.hide()

    settings.card.unlock()
    settings.card.uncollapse()
    card.collapse()


def read_assets():
    sly.logger.debug("Trying to read the Assets primitives data from API.")

    team_info = g.STATE.assets_api.team.get_info_by_name(g.ASSETS_TEAM)
    workspaces = sorted(
        g.STATE.assets_api.workspace.get_list(team_info.id), key=lambda x: x.name
    )

    sly.logger.info(
        f"Succesfully read {len(workspaces)} workspaces in {team_info.name}."
    )

    for workspace in workspaces:
        project_list = sorted(
            g.STATE.assets_api.project.get_list(workspace.id), key=lambda x: x.name
        )
        g.STATE.ASSETS.data[workspace.name] = project_list

    sly.logger.info(
        "Successfully read all projects from Assets primitives and saved them in global state."
    )


def clean_static_dir():
    """Deletes all files from the static directory except the placeholder image."""
    static_files = os.listdir(g.STATIC_DIR)

    sly.logger.debug(
        f"Cleaning static directory. Number of files to delete: {len(static_files)}."
    )

    for static_file in static_files:
        os.remove(os.path.join(g.STATIC_DIR, static_file))


@change_project_button.click
def change_project():
    select_project.enable()
    load_button.show()
    change_project_button.hide()
    input_tabs.enable()
    project_thumbnail.hide()
    g.STATE.selected_project = None

    settings.card.lock()
    settings.card.collapse()


@check_key_button.click
def connect_to_assets():
    """Checks the connection to the assets instance with specified API key."""
    check_result.hide()

    if not g.STATE.assets_api_key:
        # Reading the API key from the input widget, if it was not loaded from the team files.
        g.STATE.assets_api_key = key_input.get_value()

    try:
        g.STATE.assets_api = sly.Api(
            server_address=g.ASSETS_ADDRESS,
            token=g.STATE.assets_api_key,
            ignore_task_id=True,
        )

        g.STATE.assets_api.team.get_free_name("test")
        sly.logger.info("The connection to the Assets API was successful.")

    except (ValueError, requests.exceptions.HTTPError):
        g.STATE.assets_api_key = None
        g.STATE.assets_api = None
        sly.logger.warning("The connection to the Assets API failed.")
        check_result.text = "The connection to the Assets API failed, check the key."
        check_result.status = "error"
        check_result.show()
        return

    if g.STATE.from_team_files:
        # If the app was started from the team files, making changes in the GUI state.
        key_input.set_value(g.STATE.assets_api_key)
        change_key_button.hide()
        key_input.disable()

        input_tabs.set_active_tab("Assets")

    input_tabs.disable()

    check_result.text = f"Successfully connected to: {g.ASSETS_ADDRESS}"
    check_result.status = "success"
    check_result.show()

    # Disabling fields for entering API key if the connection was successful.
    key_input.disable()

    load_data()
    check_key_button.hide()

    if not g.STATE.from_team_files:
        change_key_button.show()


@change_key_button.click
def change_key():
    """Handles the change instance button click event."""
    key_input.enable()

    input_tabs.enable()

    check_key_button.show()
    change_key_button.hide()

    settings.card.lock()
    settings.card.collapse()

    g.STATE.assets_api_key = None
    g.STATE.assets_api = None


g.key_from_file()
# Trying to load the API key and instance address from the team files.
if g.STATE.assets_api_key:
    g.STATE.from_team_files = True
    connect_to_assets()
    file_loaded_info.show()

if g.STATE.selected_project:
    load_project()
