import os

import supervisely as sly

import globals as g
from generate import synthesize, update_bg_images
from init_ui import (init_augs, init_classes_stats, init_input_project,
                     init_progress, init_res_project, refresh_progress_images)
from postprocess import highlight_instances, postprocess


@g.app.callback("cache_annotations")
@sly.timeit
def cache_annotations(api: sly.Api, task_id, context, state, app_logger):
    progress = sly.Progress("Cache annotations", g.project_info.items_count)
    for dataset in api.dataset.get_list(g.project_id):
        images = api.image.get_list(dataset.id)
        for batch in sly.batched(images):
            image_ids = [image_info.id for image_info in batch]
            ann_infos = api.annotation.download_batch(dataset.id, image_ids)
            for image_id, image_info, ann_info in zip(image_ids, batch, ann_infos):
                ann = sly.Annotation.from_json(ann_info.annotation, g.meta)
                g.anns[image_id] = ann
                g.images_info[image_id] = image_info
                for label in ann.labels:
                    g.labels[label.obj_class.name][image_id].append(label)
            progress.iters_done_report(len(batch))

    progress = sly.Progress("App is ready", 1)
    progress.iter_done_report()


@g.app.callback("select_all_classes")
@sly.timeit
def select_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [True] * len(g.meta.obj_classes))


@g.app.callback("deselect_all_classes")
@sly.timeit
def deselect_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [False] * len(g.meta.obj_classes))


@g.app.callback("preview")
@sly.timeit
def preview(api: sly.Api, task_id, context, state, app_logger):
    bg_images = update_bg_images(api, state)

    if len(bg_images) == 0:
        sly.logger.warn("There are no background images")
    else:
        cache_dir = os.path.join(g.app.data_dir, "cache_images_preview")
        sly.fs.mkdir(cache_dir)
        sly.fs.clean_dir(cache_dir)
        img, ann, res_meta = synthesize(
            api, task_id, state, g.meta, g.images_info, g.labels, bg_images, cache_dir
        )
        res_meta, ann = postprocess(state, ann, res_meta, sly.ProjectMeta())
        if state["taskType"] == "inst-seg" and state["highlightInstances"] is True:
            res_meta, ann = highlight_instances(res_meta, ann)
        src_img_path = os.path.join(cache_dir, "res.png")
        dst_img_path = os.path.join(f"/flying_object/{task_id}", "res.png")
        sly.image.write(src_img_path, img)

        if api.file.exists(g.team_id, dst_img_path):
            api.file.remove(g.team_id, dst_img_path)
        file_info = api.file.upload(g.team_id, src_img_path, dst_img_path)

        gallery = dict(g.empty_gallery)
        gallery["content"]["projectMeta"] = res_meta.to_json()
        gallery["content"]["annotations"] = {
            "preview": {
                "url": file_info.storage_path,
                "figures": [label.to_json() for label in ann.labels],
            }
        }
        gallery["content"]["layout"] = [["preview"]]

    fields = [
        {"field": "data.gallery", "payload": gallery},
        {"field": "state.previewLoading", "payload": False},
    ]
    api.task.set_fields(task_id, fields)


@g.app.callback("generate")
@sly.timeit
def generate(api: sly.Api, task_id, context, state, app_logger):
    bg_images = update_bg_images(api, state)

    if len(bg_images) == 0:
        sly.logger.warn("There are no background images")
    else:
        cache_dir = os.path.join(g.app.data_dir, "cache_images_generate")
        sly.fs.mkdir(cache_dir)
        sly.fs.clean_dir(cache_dir)

        if state["destProject"] == "newProject":
            res_project_name = state["resProjectName"]
            if res_project_name == "":
                res_project_name = "synthetic"
            res_project = api.project.create(
                g.workspace_id, res_project_name, change_name_if_conflict=True
            )
        elif state["destProject"] == "existingProject":
            res_project = api.project.get_info_by_id(state["destProjectId"])

        res_dataset = api.dataset.get_or_create(res_project.id, state["resDatasetName"])
        res_meta = sly.ProjectMeta.from_json(api.project.get_meta(res_project.id))
        if state["backgroundLabels"] == "smartMerge":
            g.bg_meta = sly.ProjectMeta.from_json(api.project.get_meta(state["bgProjectId"]))

        progress = sly.Progress("Generating images", state["imagesCount"])
        refresh_progress_images(api, task_id, progress)
        for i in range(state["imagesCount"]):
            img, ann, cur_meta = synthesize(
                api,
                task_id,
                state,
                g.meta,
                g.images_info,
                g.labels,
                bg_images,
                cache_dir,
                preview=False,
            )
            merged_meta, new_ann = postprocess(state, ann, cur_meta, res_meta)
            if res_meta != merged_meta:
                api.project.update_meta(res_project.id, merged_meta.to_json())
                res_meta = merged_meta
            image_info = api.image.upload_np(
                res_dataset.id, f"{i + res_dataset.items_count}.png", img
            )
            api.annotation.upload_ann(image_info.id, new_ann)
            progress.iter_done_report()
            if progress.need_report():
                refresh_progress_images(api, task_id, progress)

    res_project = api.project.get_info_by_id(res_project.id)
    fields = [
        {"field": "data.started", "payload": False},
        {"field": "data.resProjectId", "payload": res_project.id},
        {"field": "data.resProjectName", "payload": res_project.name},
        {
            "field": "data.resProjectPreviewUrl",
            "payload": api.image.preview_url(res_project.reference_image_url, 100, 100),
        },
    ]
    api.task.set_fields(task_id, fields)
    # app.stop()


def main():
    data = {}
    state = {}

    init_input_project(g.app.public_api, data, g.project_info)

    # background tab
    state["tabName"] = "Backgrounds"
    state["teamId"] = g.team_id
    state["workspaceId"] = g.workspace_id
    state["bgProjectId"] = None  # project_id
    state["bgDatasets"] = []
    state["allDatasets"] = True
    state["backgroundLabels"] = "ignore"

    # classes tab
    init_classes_stats(g.app.public_api, data, state, g.project_info, g.meta)

    # augmentations tab
    init_augs(state)
    state["taskType"] = "inst-seg"
    state["highlightInstances"] = False

    # gallery
    data["gallery"] = g.empty_gallery
    state["previewLoading"] = False

    init_progress(data)
    init_res_project(data, state)
    state["destProject"] = "newProject"
    state["resDatasetName"] = "ds0"
    state["destProjectId"] = None
    state["resProjectName"] = f"synthetic_{g.project_info.name}"
    state["imagesCount"] = 10

    # @TODO: ONLY for debug
    # state["bgProjectId"] = project_id
    # state["bgDatasets"] = ["01_background"]
    # state["allDatasets"] = True
    # state["tabName"] = "Classes"

    # @TODO: ONLY for debug
    # state["bgProjectId"] = 2068
    # state["bgDatasets"] = []
    # state["allDatasets"] = True
    # state["tabName"] = "Classes"

    g.app.run(data=data, state=state, initial_events=[{"command": "cache_annotations"}])


# @TODO: ElasticTransformation
# @TODO: keep foreground w%/h% on background image
# @TODO: handle invalid augementations from user (validate augmentations)
# @TODO: check sum of objects for selected classes - disable buttons
# @TODO: output resolution
if __name__ == "__main__":
    sly.main_wrapper("main", main)
