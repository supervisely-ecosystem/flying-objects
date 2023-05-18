import supervisely as sly

from supervisely.app.widgets import (
    Card,
    Container,
    Field,
    Button,
    Tabs,
    SelectProject,
    SelectDataset,
    Checkbox,
    Select,
    ClassesTable,
    Editor,
    RadioGroup,
    Text,
    Flexbox,
    Collapse,
    Grid,
)

import src.globals as g

select_project = SelectProject(workspace_id=g.STATE.selected_workspace)
use_all_datasets_checkbox = Checkbox("Use all datasets", checked=True)
select_dataset = SelectDataset(compact=True, project_id=0)
select_dataset.hide()

labels_mode_select = Select(
    [Select.Item(value, label) for label, value in g.LABEL_MODES.items()],
)
labels_mode_field = Field(
    labels_mode_select,
    "Labels on background images",
    "Choose what to do with existing labels on background images.",
)

background_tab_container = Container(
    [select_project, use_all_datasets_checkbox, select_dataset, labels_mode_field]
)

classes_table = ClassesTable()
classes_table.hide()

classes_collapse = Collapse(labels=["test"], contents=["test"])

classes_tab_container = Container([classes_table, classes_collapse])


augmentations_tab = Editor(
    initial_text=g.STATE.augs, language_mode="yaml", height_lines=25
)

output_task_type = RadioGroup(
    [RadioGroup.Item(value, label) for label, value in g.TASK_TYPES.items()],
    direction="vertical",
)
output_task_field = Field(
    title="Output task type",
    description="How final labels have to be processed (learn more in readme).",
    content=output_task_type,
)

output_task_text = Text(status="info", text=g.TASK_TOOLTIPS["segmentation"])

random_colors_checkbox = Checkbox("Use random colors")
random_colors_field = Field(
    title="Random colors",
    description="Use random colors to highlight object instances in Preview",
    content=random_colors_checkbox,
)
random_colors_field.hide()

postprocessing_tab_container = Container(
    [output_task_field, output_task_text, random_colors_field]
)

settings_tabs = Tabs(
    ["Backgrounds", "Classes", "Augmentations", "Postprocessing"],
    [
        background_tab_container,
        classes_tab_container,
        augmentations_tab,
        postprocessing_tab_container,
    ],
)
save_settings_button = Button("Save settings", icon="zmdi zmdi-floppy")
change_settings_button = Button(
    "Change settings", icon="zmdi zmdi-swap-vertical-circle"
)
change_settings_button.hide()
buttons_flexbox = Flexbox([save_settings_button, change_settings_button])

widgets = [
    settings_tabs,
    select_project,
    select_dataset,
    use_all_datasets_checkbox,
    labels_mode_select,
    classes_table,
    classes_collapse,
    augmentations_tab,
    output_task_type,
    random_colors_checkbox,
]

card = Card(
    title="2️⃣ Settings",
    description="Configure parameters of synthetic data generation.",
    content=Container([settings_tabs, buttons_flexbox]),
    collapsable=True,
    lock_message="Choose input data on step 1️⃣.",
)
card.lock()
card.collapse()


@output_task_type.value_changed
def update_tooltip(type):
    output_task_text.text = g.TASK_TOOLTIPS[type]
    if type == "instance_segmentation":
        random_colors_field.show()
    else:
        random_colors_field.hide()


@use_all_datasets_checkbox.value_changed
def all_datasets(use):
    select_dataset._project_id = select_project.get_selected_id()
    select_dataset.update_data()
    select_dataset.update_state()
    if use:
        select_dataset.hide()
    else:
        select_dataset.show()


@save_settings_button.click
def save_settings():
    save_settings_button.hide()
    change_settings_button.show()

    for widget in widgets:
        widget.disable()


@change_settings_button.click
def change_settings():
    save_settings_button.show()
    change_settings_button.hide()

    for widget in widgets:
        widget.enable()


def load_assets():
    sly.logger.debug("Starting to load data from Assets and creating checkboxes.")
    collapse_items = []

    for workspace, project_infos in g.STATE.ASSETS.data.items():
        checkboxes = {
            "all": Checkbox("All"),
        }

        sly.logger.debug(
            f"Trying to create {len(project_infos)} checkboxes for {workspace} workspace."
        )

        for project_info in project_infos:
            checkboxes[project_info.name] = Checkbox(project_info.name)

        g.STATE.ASSETS.checkboxes[workspace] = checkboxes

        grid = Grid(columns=5, widgets=list(checkboxes.values()))

        # container = Container(list(checkboxes.values()))

        collapse_items.append(
            Collapse.Item(
                title=workspace,
                content=grid,
            )
        )

        sly.logger.debug(
            f"Succesfully created {len(project_infos)} checkboxes and added them to collapse items."
        )

    sly.logger.debug(
        "Finished loading data from Assets and creating checkboxes. "
        f"Tring to add {len(collapse_items)} collapse items to collapse widget."
    )

    classes_collapse._items = collapse_items
    classes_collapse.update_data()
    classes_collapse.update_state()

    sly.logger.info("Successfully loaded data from Assets and updated collapse widget.")

    checkboxes_all = [
        workspace["all"] for workspace in g.STATE.ASSETS.checkboxes.values()
    ]
    names_all = g.STATE.ASSETS.checkboxes.keys()

    lst = {}
    for chb, name in zip(checkboxes_all, names_all):
        lst[name] = chb.value_changed(func, name=name)

    print(len(checkboxes_all))


def func(is_checked, name=None):
    print("test", is_checked, name)
