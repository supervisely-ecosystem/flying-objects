import os
import supervisely_lib as sly
from init_ui import init_input_project

app: sly.AppService = sly.AppService()

team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])
project_id = int(os.environ['modal.state.slyProjectId'])

project_info = app.public_api.project.get_info_by_id(project_id)
if project_info is None:
    raise RuntimeError(f"Project id={project_id} not found")

meta: sly.ProjectMeta = sly.ProjectMeta(app.public_api.project.get_meta(project_id))
anns = {}


# CNT_GRID_COLUMNS = 3
# gallery = {
#     "content": {
#         "projectMeta": sly.ProjectMeta().to_json(),
#         "annotations": {},
#         "layout": [[] for i in range(CNT_GRID_COLUMNS)]
#     },
#     "previewOptions": {
#         "enableZoom": True,
#         "resizeOnZoom": True
#     },
#     "options": {
#         "enableZoom": False,
#         "syncViews": False,
#         "showPreview": True,
#         "selectable": True
#     }
# }
# gallery2tag = {}


@app.callback("init")
@sly.timeit
def init(api: sly.Api, task_id, context, state, app_logger):
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


@app.callback("assign_tag")
@sly.timeit
def assign_tag(api: sly.Api, task_id, context, state, app_logger):
    pass


def main():
    data = {}
    state = {}

    init_input_project(app.public_api, data, project_info)

    app.run(data=data, state=state, initial_events=[{"command": "init"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)
