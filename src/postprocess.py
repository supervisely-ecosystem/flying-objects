import supervisely_lib as sly


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