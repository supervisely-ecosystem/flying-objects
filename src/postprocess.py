import supervisely_lib as sly
import rasterize


def postprocess(state, ann: sly.Annotation, cur_meta: sly.ProjectMeta, res_meta: sly.ProjectMeta):
    merged_meta = None
    task_type = state["taskType"]
    if task_type == "seg":
        raise NotImplementedError()
    elif task_type == "det":
        raise NotImplementedError()
    elif task_type == "inst-seg":
        merged_meta = res_meta.merge(cur_meta)
        pass
    return ann, merged_meta


def transform_for_detection(ann: sly.Annotation, cur_meta: sly.ProjectMeta):
    # rasterize masks

    # remove labels with empty mask (remove fully occluded objects)
    pass