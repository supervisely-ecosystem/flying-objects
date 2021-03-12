import os
from collections import defaultdict
import supervisely_lib as sly

from init_ui import init_input_project, init_classes_stats, init_augs
from generate import update_bg_images, synthesize

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

images_info = {}
anns = {}
labels = defaultdict(lambda: defaultdict(list))


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
        for batch in sly.batched(images):
            image_ids = [image_info.id for image_info in batch]
            ann_infos = api.annotation.download_batch(dataset.id, image_ids)
            for image_id, image_info, ann_info in zip(image_ids, batch, ann_infos):
                ann = sly.Annotation.from_json(ann_info.annotation, meta)
                anns[image_id] = ann
                images_info[image_id] = image_info
                for label in ann.labels:
                    labels[label.obj_class.name][image_id].append(label)
        progress.iters_done_report(len(batch))


@app.callback("select_all_classes")
@sly.timeit
def select_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [True] * len(meta.obj_classes))


@app.callback("deselect_all_classes")
@sly.timeit
def deselect_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [False] * len(meta.obj_classes))


@app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    bg_images = update_bg_images(api, state)

    if len(bg_images) == 0:
        sly.logger.warn("There are no background images")
    else:
        synthesize(api, state, project_info, meta, images_info, anns, labels, bg_images)
        #img, ann =

    fields = [
        {"field": "state.previewLoading", "payload": False},
    ]
    api.task.set_fields(task_id, fields)


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
    state["previewLoading"] = False

    # ONLY for debug
    state["bgProjectId"] = project_id
    state["bgDatasets"] = ["01_background"]
    state["allDatasets"] = False
    state["tabName"] = "Classes"

    app.run(data=data, state=state, initial_events=[{"command": "cache_annotations"}])

#@TODO: fg->bg range w/h%???
#@TODO: handle invalid augementations from user
#@TODO: cache images and then clear cache on finish
#@TODO: validate augmentations - or get default value from original config if key not found
#@TODO: check sum of objects for selected classes - disable buttons
#@TODO: rasterize labels before use this app
#@TODO output project and task type
# @TODO: semi-automatic augs builder # https://stackoverflow.com/questions/334655/passing-a-dictionary-to-a-function-as-keyword-parameters
# https://www.pyimagesearch.com/2017/01/02/rotate-images-correctly-with-opencv-and-python/
if __name__ == "__main__":
    sly.fs.clean_dir("../images") # @TODO: for debug
    sly.main_wrapper("main", main)
