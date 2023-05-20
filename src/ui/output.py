from typing import Optional
from datetime import datetime

import supervisely as sly

from supervisely.app.widgets import (
    Container,
    Card,
    DestinationProject,
    InputNumber,
    Field,
    Button,
    ProjectThumbnail,
    Progress,
    Text,
)

import src.globals as g
from src.postprocess import postprocess  # , highlight_instances
import src.ui.preview as preview

images_count_input = InputNumber(10, min=1)
images_count_field = Field(
    images_count_input,
    title="Images count",
    description="How many images to generate.",
)

destination = DestinationProject(
    workspace_id=g.STATE.selected_workspace, project_type="images"
)

generate_button = Button("Generate")
stop_button = Button("Stop", button_type="danger", icon="zmdi zmdi-stop")
stop_button.hide()

generate_progress = Progress()
generate_progress.hide()

result_text = Text()
result_text.hide()

project_thumbnail = ProjectThumbnail()
project_thumbnail.hide()

card = Card(
    title="4️⃣ Output",
    description="Select a project to save the generated images and labels.",
    content=Container(
        [
            images_count_field,
            destination,
            generate_button,
            stop_button,
            generate_progress,
            result_text,
            project_thumbnail,
        ]
    ),
    lock_message="Save settings on step 2️⃣.",
    collapsable=True,
)
card.lock()
card.collapse()


@generate_button.click
def generate():
    sly.logger.debug("Generate button was clicked.")
    project_id = destination.get_selected_project_id()
    dataset_id = destination.get_selected_dataset_id()

    result_text.hide()
    project_thumbnail.hide()

    generate_button.hide()
    stop_button.show()

    sly.logger.debug(
        f"Readed values from destination widget. "
        f"Project ID: {project_id}, dataset ID: {dataset_id}."
    )

    if not project_id:
        sly.logger.debug("Project ID is not specified, creating a new project.")
        project_id = create_project(destination.get_project_name())
    if not dataset_id:
        sly.logger.debug("Dataset ID is not specified, creating a new dataset.")
        dataset_id = create_dataset(project_id, destination.get_dataset_name())

    dataset_info = g.api.dataset.get_info_by_id(dataset_id)

    res_project_meta = sly.ProjectMeta.from_json(g.api.project.get_meta(project_id))

    # Probably won't be used, since synthesize() function has this code, BUT
    # in case something goes wrong with project metas and ENABLED label merging
    # this code maybe will help debug the problem.

    # By the way, it should be deleted if successfully tested.

    # if g.STATE.SETTINGS.label_mode == "merge":
    #    background_project_meta_json = g.api.project.get_meta(
    #        g.STATE.SETTINGS.background_project_id
    #    )
    #    background_project_meta = sly.ProjectMeta.from_json(
    #        background_project_meta_json
    #    )

    images_count = images_count_input.get_value()

    sly.logger.debug(f"Readed images count: {images_count} from the input widget.")

    generate_progress.show()

    with generate_progress(message="Generating images...", total=images_count) as pbar:
        for i in range(images_count):
            if not g.STATE.continue_generation:
                sly.logger.debug("Stop button was clicked, stopping generation.")
                break
            sly.logger.debug(f"Trying to synthesize an image #{i + 1}...")

            img, ann, cur_meta = preview.synthesize()

            sly.logger.debug(f"Synthesized an image #{i + 1}. Postprocessing...")

            merged_meta, new_ann = postprocess(ann, cur_meta, res_project_meta)

            sly.logger.debug(f"Postprocessed an image #{i + 1}. Checking meta...")

            # This functionality is supposed to be working only with preview.
            # If launched while generating it will cause to change names of the classes.
            # Probably it won't be needed and should be deleted.

            # if (
            #    g.STATE.SETTINGS.task_type == "instance_segmentation"
            #    and g.STATE.SETTINGS.random_colors is True
            # ):
            #    merged_meta, new_ann = highlight_instances(merged_meta, new_ann)

            if res_project_meta != merged_meta:
                sly.logger.debug("Meta was changed, updating project meta...")

                g.api.project.update_meta(project_id, merged_meta.to_json())
                res_project_meta = merged_meta

            sly.logger.debug(f"Meta was checked for image #{i + 1}. Uploading...")

            image_info = g.api.image.upload_np(
                dataset_id, f"{i + dataset_info.items_count}.png", img
            )

            sly.logger.debug(f"Uploaded an image #{i + 1}. Uploading annotation...")

            g.api.annotation.upload_ann(image_info.id, new_ann)

            sly.logger.debug(f"Uploaded annotation for image #{i + 1}.")

            pbar.update(1)

    sly.logger.info(
        f"Finished uploading {images_count} images to project {project_id}."
    )

    if g.STATE.continue_generation:
        result_text.text = f"Successfully uploaded {images_count} images."
        result_text.status = "success"

    else:
        result_text.text = f"Uploading was stopped after {i + 1} images."
        result_text.status = "warning"

    result_text.show()

    project_thumbnail.set(g.api.project.get_info_by_id(project_id))
    project_thumbnail.show()

    generate_button.show()
    stop_button.hide()


@stop_button.click
def stop_generation():
    g.STATE.continue_generation = False
    stop_button.hide()


def create_project(project_name: Optional[str]) -> int:
    if not project_name:
        sly.logger.info("Project name is not specified, using 'synthetic'.")
        project_name = "synthetic"

    project = g.api.project.create(
        g.STATE.selected_workspace, project_name, change_name_if_conflict=True
    )
    return project.id


def create_dataset(project_id: int, dataset_name: Optional[str]) -> int:
    if not dataset_name:
        sly.logger.debug("Dataset name is not specified, using timestamp.")
        dataset_name = datetime.now().strftime("%Y-%m-%d %H:%M")

    dataset = g.api.dataset.create(
        project_id, dataset_name, change_name_if_conflict=True
    )
    return dataset.id
