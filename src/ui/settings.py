import supervisely as sly

import yaml
import urllib.parse


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
    ReloadableArea,
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

classes_collapse = Collapse()
classes_ra = ReloadableArea(content=classes_collapse)

classes_tab_container = Container([classes_table, classes_ra])


augmentations_editor = Editor(
    initial_text=g.STATE.augs, language_mode="yaml", height_lines=25
)

advanced_options_checkbox = Checkbox("Advanced mode")
advanced_options_field = Field(
    title="Use advanced augmentation options",
    description="You can set custom class distribution and size ranges for each class.",
    content=advanced_options_checkbox,
)
advanced_options_editor = Editor(language_mode="yaml", height_lines=40)
advanced_options_editor.hide()

advanced_options_text = Text(
    "Advanced options will override the settings below.", status="info"
)
advanced_options_text.hide()

augmentations_tab_containter = Container(
    widgets=[
        advanced_options_field,
        advanced_options_editor,
        advanced_options_text,
        augmentations_editor,
    ]
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
        augmentations_tab_containter,
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
    augmentations_editor,
    advanced_options_checkbox,
    advanced_options_editor,
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

    selects = get_selected_classes()

    if g.STATE.assets_api:
        g.STATE.SETTINGS.use_assets = True
        g.STATE.SETTINGS.selected_primitives = selects

        sly.logger.debug(
            f"Selected primitives: {selects}, the app in Assets mode: {g.STATE.SETTINGS.use_assets}"
        )

    else:
        g.STATE.SETTINGS.use_assets = False
        g.STATE.SETTINGS.selected_classes = selects

        sly.logger.debug(
            f"Selected classes: {selects}, the app in Assets mode: {g.STATE.SETTINGS.use_assets}"
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
    augs = augmentations_editor.get_text()
    g.STATE.augs = augs if augs else None
    g.STATE.SETTINGS.augmentations = yaml.safe_load(augs)

    advanced_options = advanced_options_editor.get_text()
    g.STATE.SETTINGS.advanced_options = yaml.safe_load(advanced_options)

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


def load_assets(pbar=None):
    sly.logger.debug("Starting to load data from Assets and creating checkboxes.")
    collapse_items = []

    def create_checkbox_handler(workspace, **kwargs):
        all_checkbox = kwargs.get("all_checkbox")
        checkbox = kwargs.get("checkbox")
        if all_checkbox:

            @all_checkbox.value_changed
            def handle_checkboxes(check):
                advanced_options_editor.hide()
                advanced_options_checkbox.uncheck()
                g.STATE.SETTINGS.advanced_options = None
                if check:
                    for checkbox in g.STATE.ASSETS.checkboxes[workspace].values():
                        checkbox.check()
                else:
                    for checkbox in g.STATE.ASSETS.checkboxes[workspace].values():
                        checkbox.uncheck()

        if checkbox:

            @checkbox.value_changed
            def handle_checkbox(check):
                advanced_options_editor.hide()
                advanced_options_checkbox.uncheck()
                g.STATE.SETTINGS.advanced_options = None
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

    sly.logger.debug(
        f"Readed {len(g.STATE.ASSETS.data)} workspaces on Assets from global state, starting to create checkboxes."
    )

    for workspace_name, workspace_data in g.STATE.ASSETS.data.items():
        all_checkbox = Checkbox("All")
        checkboxes = {"all": all_checkbox}

        sly.logger.debug(f"Creating checkboxes for {workspace_name} workspace.")

        for project_data in workspace_data:
            project_info = project_data["project_info"]
            project_stats = g.STATE.assets_api.project.get_stats(project_info.id)
            primitives = project_data["primitives"]

            for primitive in primitives:
                class_stats = project_stats["objects"]["items"]

                objects_count = None

                for class_stat in class_stats:
                    if class_stat["objectClass"]["name"] == primitive.name:
                        objects_count = class_stat["total"]
                        break

                if not objects_count:
                    continue

                primitive_url = (
                    g.WEB_ADDRESS
                    + f"{urllib.parse.quote(project_info.name).lower()}-{project_info.id}/"
                )

                text = Text(
                    f"{primitive.widget_name} <a href='{primitive_url}'>({objects_count})</a>"
                )

                checkbox = Checkbox(text)
                checkboxes[primitive.name] = checkbox
                create_checkbox_handler(workspace_name, checkbox=checkbox)

        g.STATE.ASSETS.checkboxes[workspace_name] = checkboxes

        create_checkbox_handler(workspace_name, all_checkbox=all_checkbox)

        grid = Grid(columns=5, widgets=list(checkboxes.values()))

        collapse_items.append(
            Collapse.Item(
                name=workspace_name,
                title=workspace_name,
                content=grid,
            )
        )

        sly.logger.debug(f"Created checkboxes for {workspace_name} workspace.")

        if pbar:
            pbar.update(1)

    sly.logger.debug(
        "Finished loading data from Assets and creating checkboxes. "
        f"Tring to add {len(collapse_items)} collapse items to collapse widget."
    )

    classes_collapse.set_items(collapse_items)
    classes_collapse.show()
    classes_ra.reload()

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

    for primitive in g.STATE.SETTINGS.selected_primitives:
        if primitive.project_id not in g.STATE.ASSETS.project_ids:
            g.STATE.ASSETS.project_ids.append(primitive.project_id)
            sly.logger.debug(
                f"Added project ID {primitive.project_id} for {primitive.name} to global state."
            )

    for project_id in g.STATE.ASSETS.project_ids:
        project_meta = sly.ProjectMeta.from_json(
            g.STATE.assets_api.project.get_meta(project_id)
        )

        if res_project_meta is None:
            res_project_meta = project_meta
        else:
            res_project_meta = res_project_meta.merge(project_meta)

        sly.logger.debug(f"Successfully merged meta for {project_id}.")

    g.STATE.project_meta = res_project_meta

    sly.logger.info("Successfully merged meta from all selected projects in assets.")


@advanced_options_checkbox.value_changed
def advanced_options_handler(checked):
    if checked:
        build_advanced_options()
        advanced_options_text.show()
        advanced_options_editor.show()
    else:
        advanced_options_text.hide()
        advanced_options_editor.hide()
        g.STATE.SETTINGS.advanced_options = None


def build_advanced_options():
    selects = get_selected_classes(lock=False)
    if not selects:
        advanced_options_checkbox.uncheck()
        advanced_options_editor.hide()
        g.STATE.SETTINGS.advanced_options = None
        return

    resizes = ""
    distributions = ""
    if g.STATE.assets_api:
        class_names = [primitive.name for primitive in selects]

    else:
        class_names = selects

    parts = distribute_percentages(len(class_names))
    for class_name, part in zip(class_names, parts):
        resizes += f"    {class_name}: (0.8, 1.5)\n"
        distributions += f"    {class_name}: {part}\n"

    advanced_options = (
        "options:\n"
        "  total_objects_count: [1, 5] # total number of objects (range) per image\n"
        f"  distributions: # percent of images from total objects count for each class\n{distributions}"
        f"  resizes: # resize range for each class\n{resizes}"
    )
    advanced_options_editor.set_text(advanced_options)


def distribute_percentages(num_parts: int):
    quotient = 100 // num_parts
    remainder = 100 % num_parts

    parts = [quotient] * num_parts

    for i in range(remainder):
        parts[i] += 1

    return parts


def get_selected_classes(lock: bool = True):
    sly.logger.debug("Trying to read selected classes or primitives.")

    if g.STATE.assets_api:
        sly.logger.info(
            "The app is working with Assets API, will try to read selected primitives."
        )

        selected_primitives = []
        for workspace, checkboxes in g.STATE.ASSETS.checkboxes.items():
            for name, checkbox in checkboxes.items():
                if checkbox.is_checked() and name != "all":
                    selected_primitives.append(get_primitive(workspace, name))

        if not selected_primitives:
            error_text.text = "At least one item on class tab must be selected."
            error_text.show()
            sly.logger.warning("No primitives were selected, stopping function.")
            settings_tabs.set_active_tab("Classes")
            return

        if lock:
            for checkboxes in g.STATE.ASSETS.checkboxes.values():
                for checkbox in checkboxes.values():
                    checkbox.disable()

        sly.logger.info(
            f"Following primitives (Category: [Class]) were selected: {selected_primitives}."
        )

        return selected_primitives

    else:
        sly.logger.info("The app is working with Supervisely project.")

        selected_classes = classes_table.get_selected_classes()
        if not selected_classes:
            error_text.text = "At least one item on class tab must be selected."
            error_text.show()
            sly.logger.warning("No classes were selected, stopping function.")
            settings_tabs.set_active_tab("Classes")
            return

        sly.logger.info(f"Following classes were selected: {selected_classes}.")

        return selected_classes


def get_primitive(workspace_name, class_name):
    for project_data in g.STATE.ASSETS.data[workspace_name]:
        for primitive in project_data["primitives"]:
            if primitive.name == class_name:
                return primitive
