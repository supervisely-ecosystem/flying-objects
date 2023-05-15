import os

import supervisely as sly
from supervisely.app.widgets import (
    Card,
    SelectDataset,
    Button,
    Container,
    DatasetThumbnail,
    Text,
    Checkbox,
    Field,
)

import src.globals as g
import src.ui.keys as keys

dataset_thumbnail = DatasetThumbnail()
dataset_thumbnail.hide()

load_button = Button("Load data")
change_dataset_button = Button("Change dataset", icon="zmdi zmdi-lock-open")
change_dataset_button.hide()

no_dataset_message = Text(
    "Please, select a dataset before clicking the button.",
    status="warning",
)
no_dataset_message.hide()

if g.STATE.selected_dataset and g.STATE.selected_project:
    # If the app was loaded from a dataset.
    sly.logger.debug("App was loaded from a dataset.")

    # Stting values to the widgets from environment variables.
    select_dataset = SelectDataset(
        default_id=g.STATE.selected_dataset, project_id=g.STATE.selected_project
    )

    # Hiding unnecessary widgets.
    select_dataset.hide()
    load_button.hide()

    # Creating a dataset thumbnail to show.
    dataset_thumbnail.set(
        g.api.project.get_info_by_id(g.STATE.selected_project),
        g.api.dataset.get_info_by_id(g.STATE.selected_dataset),
    )
    dataset_thumbnail.show()

elif g.STATE.selected_project:
    # If the app was loaded from a project: showing the dataset selector in compact mode.
    sly.logger.debug("App was loaded from a project.")

    select_dataset = SelectDataset(
        project_id=g.STATE.selected_project, compact=True, show_label=False
    )
else:
    # If the app was loaded from ecosystem: showing the dataset selector in full mode.
    sly.logger.debug("App was loaded from ecosystem.")

    select_dataset = SelectDataset()

connect_to_assets_checkbox = Checkbox("Connect to Assets")
connect_to_assets_field = Field(
    content=connect_to_assets_checkbox,
    title="Use primitives from Assets",
    description="Connect to Assets API using the API key to use the primitives in the app.",
)

# Input card with all widgets.
card = Card(
    "1️⃣ Input dataset",
    "Images from the selected dataset will be loaded.",
    content=Container(
        widgets=[
            dataset_thumbnail,
            select_dataset,
            load_button,
            change_dataset_button,
            connect_to_assets_field,
            no_dataset_message,
        ]
    ),
    collapsable=True,
)


@load_button.click
def load_dataset():
    """Handles the load button click event. Reading values from the SelectDataset widget,
    calling the API to get project, workspace and team ids (if they're not set),
    building the table with images and unlocking the rotator and output cards.
    """
    # Reading the dataset id from SelectDataset widget.
    dataset_id = select_dataset.get_selected_id()

    if not dataset_id:
        # If the dataset id is empty, showing the warning message.
        no_dataset_message.show()
        return

    # Hide the warning message if dataset was selected.
    no_dataset_message.hide()

    # Changing the values of the global variables to access them from other modules.
    g.STATE.selected_dataset = dataset_id

    # Cleaning the static directory when the new dataset is selected.
    clean_static_dir()

    # Disabling the dataset selector and the load button.
    select_dataset.disable()
    load_button.hide()

    # Showing the lock checkbox for unlocking the dataset selector and button.
    change_dataset_button.show()

    sly.logger.debug(
        f"Calling API with dataset ID {dataset_id} to get project, workspace and team IDs."
    )

    g.STATE.selected_project = g.api.dataset.get_info_by_id(dataset_id).project_id
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

    dataset_thumbnail.set(
        g.api.project.get_info_by_id(g.STATE.selected_project),
        g.api.dataset.get_info_by_id(g.STATE.selected_dataset),
    )
    dataset_thumbnail.show()


def clean_static_dir():
    """Deletes all files from the static directory except the placeholder image."""
    static_files = os.listdir(g.STATIC_DIR)

    sly.logger.debug(
        f"Cleaning static directory. Number of files to delete: {len(static_files)}."
    )

    for static_file in static_files:
        os.remove(os.path.join(g.STATIC_DIR, static_file))


@change_dataset_button.click
def handle_input():
    """Handles the change dataset button click event. Enabling the dataset selector
    and the load button, hiding the change dataset button.
    """
    select_dataset.enable()
    load_button.show()
    change_dataset_button.hide()


@connect_to_assets_checkbox.value_changed
def assets_card_handler(show):
    if show:
        keys.card.show()
        keys.card.uncollapse()
    else:
        keys.card.hide()
        keys.card.collapse()
