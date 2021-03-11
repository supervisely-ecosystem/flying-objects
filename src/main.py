import os
import supervisely_lib as sly
from init_ui import init_input_project, init_classes_stats, init_augs

app: sly.AppService = sly.AppService()

team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])
project_id = int(os.environ['modal.state.slyProjectId'])

project_info = app.public_api.project.get_info_by_id(project_id)
if project_info is None:
    raise RuntimeError(f"Project id={project_id} not found")

meta = sly.ProjectMeta.from_json(app.public_api.project.get_meta(project_id))
if len(meta.obj_classes) == 0:
    raise ValueError("Project should have at least one class")

anns = {}

background_datasets = []
background_images = []

CNT_GRID_COLUMNS = 1
empty_gallery = {
    "content": {
        "projectMeta": sly.ProjectMeta().to_json(),
        "annotations": {},
        "layout": [[] for i in range(CNT_GRID_COLUMNS)]
    },
    "previewOptions": {
        "enableZoom": True,
        "resizeOnZoom": True
    },
    "options": {
        "enableZoom": True,
        "syncViews": False,
        "showPreview": True,
        "selectable": False
    }
}


@app.callback("cache_annotations")
@sly.timeit
def cache_annotations(api: sly.Api, task_id, context, state, app_logger):
    progress = sly.Progress("Cache annotations", project_info.items_count)
    for dataset in api.dataset.get_list(project_id):
        images = api.image.get_list(dataset.id)
        image_ids = [image_info.id for image_info in images]
        for batch in sly.batched(image_ids):
            ann_infos = api.annotation.download_batch(dataset.id, batch)
            for image_id, ann_info in zip(batch, ann_infos):
                ann = sly.Annotation.from_json(ann_info.annotation, meta)
                anns[image_id] = ann
        progress.iters_done_report(len(batch))


@app.callback("select_all_classes")
@sly.timeit
def select_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [True] * len(meta.obj_classes))


@app.callback("deselect_all_classes")
@sly.timeit
def deselect_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [False] * len(meta.obj_classes))


@app.callback("preview_random")
@sly.timeit
def preview_random(api: sly.Api, task_id, context, state, app_logger):
    bg_project_id = state["bgProjectId"]
    if bg_project_id is None:
        return


def main():
    data = {}
    state = {}

    init_input_project(app.public_api, data, project_info)

    # background tab
    state["tabName"] = "Backgrounds"
    state["teamId"] = team_id
    state["workspaceId"] = workspace_id
    state["bgProjectId"] = None # project_id
    state["bgDatasets"] = []
    state["allDatasets"] = True

    #classes tab
    init_classes_stats(app.public_api, data, state, project_info, meta)

    #augmentations tab
    init_augs(state)

    # gallery
    data["gallery"] = empty_gallery

    app.run(data=data, state=state, initial_events=[{"command": "cache_annotations"}])


#@TODO: raise error Project does not have any classes
#@TODO: background augmentations

#@TODO later:
# - result augmentations (yaml) -
# output project and task

# https://stackoverflow.com/questions/334655/passing-a-dictionary-to-a-function-as-keyword-parameters
if __name__ == "__main__":
    sly.main_wrapper("main", main)
