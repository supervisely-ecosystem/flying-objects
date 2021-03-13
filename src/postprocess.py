import numpy as np
import supervisely_lib as sly


def postprocess(state, ann: sly.Annotation, cur_meta: sly.ProjectMeta, res_meta: sly.ProjectMeta) \
        -> (sly.ProjectMeta, sly.Annotation):
    task_type = state["taskType"]
    if task_type == "seg":
        new_meta, new_ann = transform_for_segmentation(cur_meta, ann)
    elif task_type == "det":
        new_meta, new_ann = transform_for_detection(cur_meta, ann)
    elif task_type == "inst-seg":
        new_meta, new_ann = cur_meta, ann
    merged_meta = res_meta.merge(new_meta)
    return merged_meta, new_ann


def transform_for_detection(meta: sly.ProjectMeta, ann: sly.Annotation) -> (sly.ProjectMeta, sly.Annotation):
    new_classes = sly.ObjClassCollection()
    new_labels = []
    for label in ann.labels:
        if label.obj_class.geometry_type is sly.Rectangle:
            new_labels.append(label)
            if new_classes.get(label.obj_class.name) is None:
                new_classes = new_classes.add(label.obj_class)
        else:
            bbox = label.geometry.to_bbox()
            new_class = new_classes.get(label.obj_class.name)
            if new_class is None:
                new_class = label.obj_class.clone(geometry_type=sly.Rectangle)
                new_classes = new_classes.add(new_class)
            new_labels.append(label.clone(bbox, new_class))
    res_meta = meta.clone(obj_classes=new_classes)
    res_ann = ann.clone(labels=new_labels)
    return (res_meta, res_ann)


def transform_for_segmentation(meta: sly.ProjectMeta, ann: sly.Annotation) -> (sly.ProjectMeta, sly.Annotation):
    new_classes = []
    class_masks = {}
    for obj_class in meta.obj_classes:
        obj_class: sly.ObjClass
        if obj_class.geometry_type is not sly.Bitmap:
            new_classes.append(obj_class.clone(geometry_type=sly.Bitmap))
        else:
            new_classes.append(obj_class)
        class_masks[obj_class.name] = np.zeros(ann.img_size, np.uint8)

    new_class_collection = sly.ObjClassCollection(new_classes)
    for label in ann.labels:
        label.draw(class_masks[label.obj_class.name], color=255)

    new_labels = []
    for class_name, white_mask in class_masks.items():
        mask = white_mask == 255
        obj_class = new_class_collection.get(class_name)
        bitmap = sly.Bitmap(data=mask)
        new_labels.append(sly.Label(geometry=bitmap, obj_class=obj_class))

    res_meta = meta.clone(obj_classes=new_class_collection)
    res_ann = ann.clone(labels=new_labels)
    return (res_meta, res_ann)


def highlight_instances(meta: sly.ProjectMeta, ann: sly.Annotation) -> (sly.ProjectMeta, sly.Annotation):
    new_classes = []
    new_labels = []
    for idx, label in enumerate(ann.labels):
        new_cls = label.obj_class.clone(name=str(idx), color=sly.color.random_rgb())
        new_lbl = label.clone(obj_class=new_cls)

        new_classes.append(new_cls)
        new_labels.append(new_lbl)

    res_meta = meta.clone(obj_classes=sly.ObjClassCollection(new_classes))
    res_ann = ann.clone(labels=new_labels)
    return (res_meta, res_ann)