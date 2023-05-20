import supervisely as sly

import yaml
import urllib.parse

from collections import defaultdict

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
    Progress,
)

import src.globals as g
import src.ui.preview as preview
import src.ui.output as output

select_project = SelectProject(workspace_id=g.STATE.selected_workspace)
use_all_datasets_checkbox = Checkbox("Use all datasets", checked=True)
select_dataset = SelectDataset(compact=True, project_id=0)
select_dataset.hide()

error_text = Text(status="error")
error_text.hide()

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

caching_progress = Progress()
caching_progress.hide()

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
    content=Container(
        [settings_tabs, save_settings_button, error_text, caching_progress]
    ),
    collapsable=True,
    lock_message="Choose input data on step 1️⃣.",
    content_top_right=change_settings_button,
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
    error_text.hide()

    sly.logger.debug("Save settings button was clicked.")

    background_project_id = select_project.get_selected_id()
    if not background_project_id:
        error_text.text = "Project with backgrounds is not selected."
        error_text.show()
        settings_tabs.set_active_tab("Backgrounds")
        return

    g.STATE.SETTINGS.background_project_id = background_project_id
    sly.logger.debug(f"Selected project with backgrounds: {background_project_id}")

    if g.STATE.assets_api:
        sly.logger.info(
            "The app is working with Assets API, will try to read selected primitives."
        )

        g.STATE.SETTINGS.use_assets = True

        selected_primitives = defaultdict(list)
        for workspace, checkboxes in g.STATE.ASSETS.checkboxes.items():
            for name, checkbox in checkboxes.items():
                if checkbox.is_checked() and name != "all":
                    selected_primitives[workspace].append(name)
        if not selected_primitives:
            error_text.text = "At least one item on class tab must be selected."
            error_text.show()
            sly.logger.warning("No primitives were selected, stopping function.")
            settings_tabs.set_active_tab("Classes")
            return

        for checkboxes in g.STATE.ASSETS.checkboxes.values():
            for checkbox in checkboxes.values():
                checkbox.disable()

        g.STATE.SETTINGS.selected_primitives = selected_primitives

        sly.logger.info(
            f"Following primitives (Category: [Class]) were selected: {selected_primitives} and saved in global state."
        )

    else:
        sly.logger.info("The app is working with Supervisely project.")

        g.STATE.SETTINGS.use_assets = False

        selected_classes = classes_table.get_selected_classes()
        if not selected_classes:
            error_text.text = "At least one item on class tab must be selected."
            error_text.show()
            sly.logger.warning("No classes were selected, stopping function.")
            settings_tabs.set_active_tab("Classes")
            return

        g.STATE.SETTINGS.selected_classes = selected_classes

        sly.logger.info(
            f"Following classes were selected: {selected_classes} and saved in global state."
        )

    save_settings_button.text = "Applying..."

    g.STATE.SETTINGS.use_all_datasets = use_all_datasets_checkbox.is_checked()
    if not g.STATE.SETTINGS.use_all_datasets:
        g.STATE.SETTINGS.background_dataset_ids = [select_dataset.get_selected_id()]
    else:
        g.STATE.SETTINGS.background_dataset_ids = [
            dataset.id for dataset in g.api.dataset.get_list(background_project_id)
        ]

    g.STATE.SETTINGS.label_mode = labels_mode_select.get_value()
    augs = augmentations_tab.get_text()
    g.STATE.augs = augs if augs else None
    g.STATE.SETTINGS.augmentations = yaml.safe_load(augs)

    sly.logger.debug(f"Readed augmentations: {g.STATE.SETTINGS.augmentations}.")

    g.STATE.SETTINGS.task_type = output_task_type.get_value()
    if g.STATE.SETTINGS.task_type == "instance_segmentation":
        g.STATE.SETTINGS.random_colors = random_colors_checkbox.is_checked()

    settings_log_message = (
        f"Settings were saved. App using assets: {g.STATE.SETTINGS.use_assets}, "
        f"project ID with backgrounds: {g.STATE.SETTINGS.background_project_id}, "
        f"using all datasets: {g.STATE.SETTINGS.use_all_datasets}. "
        f"Background datasets ID: {g.STATE.SETTINGS.background_dataset_ids}, "
        f"label mode: {g.STATE.SETTINGS.label_mode}, "
        f"selected classes: {g.STATE.SETTINGS.selected_classes} OR "
        f"selected primitives: {g.STATE.SETTINGS.selected_primitives}. "
        f"Task type: {g.STATE.SETTINGS.task_type}, "
        f"random colors: {g.STATE.SETTINGS.random_colors}."
    )

    sly.logger.info(settings_log_message)

    background_image_infos = []

    for dataset_id in g.STATE.SETTINGS.background_dataset_ids:
        background_image_infos.extend(g.api.image.get_list(dataset_id))

    g.STATE.background_image_infos = background_image_infos

    sly.logger.debug(
        f"Readed {len(background_image_infos)} background image infos and saved in the global state."
    )

    for widget in widgets:
        widget.disable()

    if g.STATE.SETTINGS.use_assets:
        download_assets()

    cache_annotations()

    preview.card.unlock()
    preview.card.uncollapse()
    output.card.unlock()
    output.card.uncollapse()

    save_settings_button.hide()
    save_settings_button.text = "Save settings"
    change_settings_button.show()

    card.collapse()

    preview.preview()
    preview.random_image_button.enable()


@change_settings_button.click
def change_settings():
    card.uncollapse()
    save_settings_button.show()
    change_settings_button.hide()
    preview.random_image_button.disable()

    preview.image_preview.clean_up()
    preview.image_preview.hide()

    g.STATE.SETTINGS.clear()
    g.STATE.ASSETS.clear()

    for checkboxes in g.STATE.ASSETS.checkboxes.values():
        for checkbox in checkboxes.values():
            checkbox.enable()

    for widget in widgets:
        widget.enable()

    preview.card.lock()
    preview.card.collapse()
    output.card.lock()
    output.card.collapse()


def load_assets():
    sly.logger.debug("Starting to load data from Assets and creating checkboxes.")
    collapse_items = []

    def create_checkbox_handler(workspace, **kwargs):
        all_checkbox = kwargs.get("all_checkbox")
        checkbox = kwargs.get("checkbox")
        if all_checkbox:

            @all_checkbox.value_changed
            def handle_checkboxes(check):
                if check:
                    for checkbox in g.STATE.ASSETS.checkboxes[workspace].values():
                        checkbox.check()
                else:
                    for checkbox in g.STATE.ASSETS.checkboxes[workspace].values():
                        checkbox.uncheck()

        if checkbox:

            @checkbox.value_changed
            def handle_checkbox(check):
                if not check:
                    g.STATE.ASSETS.checkboxes[workspace]["all"].uncheck()
                else:
                    checkboxes = [
                        (name, checkbox)
                        for name, checkbox in g.STATE.ASSETS.checkboxes[
                            workspace
                        ].items()
                        if name != "all"
                    ]

                    # Name in tuple (name, checkbox) is only for debug purposes.

                    for name, checkbox in checkboxes:
                        if checkbox.is_checked() is False:
                            return
                    g.STATE.ASSETS.checkboxes[workspace]["all"].check()

    for workspace, project_infos in g.STATE.ASSETS.data.items():
        all_checkbox = Checkbox("All")
        checkboxes = {"all": all_checkbox}

        sly.logger.debug(
            f"Trying to create {len(project_infos)} checkboxes for {workspace} workspace."
        )

        for project_info in project_infos:
            project_stats = g.STATE.assets_api.project.get_stats(project_info.id)
            object_count = project_stats["objects"]["total"]["objectsInDataset"]

            if object_count == 0:
                continue
            primitive_url = (
                g.WEB_ADDRESS
                + f"{urllib.parse.quote(project_info.name).lower()}-{project_info.id}/"
            )

            text = Text(
                f"{project_info.name} <a href='{primitive_url}'>({object_count})</a>"
            )

            checkbox = Checkbox(text)
            checkboxes[project_info.name] = checkbox
            create_checkbox_handler(workspace, checkbox=checkbox)

        g.STATE.ASSETS.checkboxes[workspace] = checkboxes

        create_checkbox_handler(workspace, all_checkbox=all_checkbox)

        grid = Grid(columns=5, widgets=list(checkboxes.values()))

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


def cache_annotations():
    sly.logger.info("Caching function for annotations was started.")

    if g.STATE.SETTINGS.use_assets:
        api = g.STATE.assets_api
        project_ids = g.STATE.ASSETS.project_ids

        sly.logger.debug(f"The app working with assets. Project IDs: {project_ids}.")

    else:
        api = g.api
        project_ids = [g.STATE.selected_project]

        sly.logger.debug(
            f"The app working with current project. Project IDs: {project_ids}."
        )

    sly.logger.debug(f"Trying to cache annotations for {len(project_ids)} projects.")

    caching_progress.show()
    with caching_progress(
        message="Caching images and annotations...", total=len(project_ids)
    ) as pbar:
        for project_id in project_ids:
            datasets = api.dataset.get_list(project_id)
            for dataset in datasets:
                image_infos = api.image.get_list(dataset.id)
                for batched_image_infos in sly.batched(image_infos):
                    batched_image_ids = [
                        image_info.id for image_info in batched_image_infos
                    ]
                    batched_ann_infos = api.annotation.download_batch(
                        dataset.id, batched_image_ids
                    )
                    for image_id, image_info, ann_info in zip(
                        batched_image_ids, batched_image_infos, batched_ann_infos
                    ):
                        ann = sly.Annotation.from_json(
                            ann_info.annotation, g.STATE.project_meta
                        )
                        g.STATE.image_infos[image_id] = image_info
                        for label in ann.labels:
                            g.STATE.labels[label.obj_class.name][image_id].append(label)
            pbar.update(1)

    sly.logger.info(
        f"Finished caching {len(g.STATE.image_infos)} images infos in global state."
    )
    sly.logger.info("Finished caching annotations for project in global state.")


def download_assets():
    res_project_meta = None

    sly.logger.debug(
        f"Starting iteration over {len(g.STATE.SETTINGS.selected_primitives)} selected categories of primitives."
    )

    for workspace_name, project_names in g.STATE.SETTINGS.selected_primitives.items():
        workspace_info = g.STATE.assets_api.workspace.get_info_by_name(
            g.ASSETS_TEAM_ID, workspace_name
        )

        sly.logger.debug(f"Retrieved workspace info for {workspace_name}.")

        for project_name in project_names:
            sly.logger.debug(
                f"Working in workspace {workspace_name} and project {project_name}."
            )

            project_info = g.STATE.assets_api.project.get_info_by_name(
                workspace_info.id, project_name
            )
            project_meta_json = g.STATE.assets_api.project.get_meta(project_info.id)
            project_meta = sly.ProjectMeta.from_json(project_meta_json)

            g.STATE.ASSETS.project_ids.append(project_info.id)
            sly.logger.debug(
                f"Added project ID {project_info.id} for {project_name} to global state."
            )

            class_names = [obj_class.name for obj_class in project_meta.obj_classes]
            g.STATE.ASSETS.class_names.extend(class_names)

            sly.logger.debug(
                f"Added {class_names} to global state. "
                f"Current number of classes in global state: {len(g.STATE.ASSETS.class_names)}."
            )

            if res_project_meta is None:
                res_project_meta = project_meta
            else:
                res_project_meta = res_project_meta.merge(project_meta)

            sly.logger.debug(f"Successfully merged meta for {project_name}.")

    g.STATE.project_meta = res_project_meta

    sly.logger.info("Successfully merged meta from all selected projects in assets.")
