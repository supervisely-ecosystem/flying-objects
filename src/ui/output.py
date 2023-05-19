from supervisely.app.widgets import (
    Container,
    Card,
    DestinationProject,
    InputNumber,
    Field,
    Button,
    ProjectThumbnail,
    Progress,
)

import src.globals as g

images_count_input = InputNumber(10, min=1)
images_count_field = Field(
    images_count_input,
    title="Images count",
    description="How many images to generate.",
)

destination_project = DestinationProject(
    workspace_id=g.STATE.selected_workspace, project_type="images"
)

generate_button = Button("Generate")
stop_button = Button("Stop", button_type="danger", icon="zmdi zmdi-stop")
stop_button.hide()

generate_progress = Progress()
generate_progress.hide()

project_thumbnail = ProjectThumbnail()
project_thumbnail.hide()

card = Card(
    title="4️⃣ Output",
    description="Select a project to save the generated images and labels.",
    content=Container(
        [
            images_count_field,
            destination_project,
            generate_button,
            stop_button,
            generate_progress,
            project_thumbnail,
        ]
    ),
    lock_message="Save settings on step 2️⃣.",
    collapsable=True,
)
card.lock()
card.collapse()


@stop_button.click
def stop_generation():
    g.STATE.continue_generation = False
    stop_button.hide()
