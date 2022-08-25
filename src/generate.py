import os
import random
from collections import defaultdict

import numpy as np
import supervisely_lib as sly
import yaml

import aug
import globals as g
import rasterize
from init_ui import refresh_progress, refresh_progress_preview

bg_project_id = None
bg_datasets = None
bg_images = None


def update_bg_images(api: sly.Api, state):
    global bg_project_id, bg_datasets, bg_images

    cur_bg_project_id = state["bgProjectId"]
    g.bg_meta = sly.ProjectMeta.from_json(
        api.project.get_meta(cur_bg_project_id)
    )

    cur_bg_datasets = state["bgDatasets"]
    if state["allDatasets"] is True:
        datasets_info = api.dataset.get_list(cur_bg_project_id)
        cur_bg_datasets = [info.name for info in datasets_info]

    if (
            bg_project_id is not None
            and bg_datasets is not None
            and bg_images is not None
            and cur_bg_project_id == bg_project_id
            and set(cur_bg_datasets) == set(bg_datasets)
    ):
        sly.logger.info("Keep previous background images")
    else:
        bg_project_id = cur_bg_project_id
        bg_datasets = cur_bg_datasets
        bg_images = []
        for dataset_name in cur_bg_datasets:
            dataset_info = api.dataset.get_info_by_name(bg_project_id, dataset_name)
            bg_images.extend(api.image.get_list(dataset_info.id))

    sly.logger.info(f"Background datasets: {bg_datasets}")
    sly.logger.info(f"Background images count: {len(bg_images)}")
    return bg_images


# @sly.timeit
def get_label_foreground(img, label):
    bbox = label.geometry.to_bbox()
    img_crop = sly.image.crop(img, bbox)
    new_label = label.translate(drow=-bbox.top, dcol=-bbox.left)
    h, w = img_crop.shape[0], img_crop.shape[1]
    mask = np.zeros((h, w, 3), np.uint8)
    new_label.draw(mask, [255, 255, 255])
    return img_crop, mask


# @sly.timeit
def augment_foreground(image, mask):
    augmented = aug.transform_fg(image=image, mask=mask)
    image_aug = augmented["image"]
    mask_aug = augmented["mask"]
    return image_aug, mask_aug


# @sly.timeit
def _get_image_using_cache(api: sly.Api, cache_dir, image_id, image_info):
    img_path = os.path.join(
        cache_dir, f"{image_id}{sly.fs.get_file_ext(image_info.name)}"
    )
    if not sly.fs.file_exists(img_path):
        api.image.download_path(image_id, img_path)
    return sly.image.read(img_path)


@sly.timeit
def synthesize(
        api: sly.Api,
        task_id,
        state,
        meta: sly.ProjectMeta,
        image_infos,
        labels,
        bg_images,
        cache_dir,
        preview=True,
):
    progress_cb = refresh_progress_preview
    if preview is False:
        progress_cb = refresh_progress
    augs = yaml.safe_load(state["augs"])
    sly.logger.info("Init augs from yaml file")
    aug.init_fg_augs(augs)
    visibility_threshold = augs["objects"].get("visibility", 0.8)
    classes = state["selectedClasses"]
    bg_info = random.choice(bg_images)
    sly.logger.info("Download background")
    bg = api.image.download_np(bg_info.id)
    sly.logger.debug(f"BG shape: {bg.shape}")

    res_labels = []
    res_classes = []
    res_classes_names = []

    to_generate = []
    res_image = bg.copy()

    for class_name in classes:
        original_class: sly.ObjClass = meta.get_obj_class(class_name)
        if original_class.name not in res_classes_names:
            res_classes.append(original_class)
        count_range = augs["objects"]["count"]
        count = random.randint(*count_range)
        for i in range(count):
            to_generate.append(class_name)
    random.shuffle(to_generate)
    res_classes = convert_res_classes_to_bitmap(res_classes)
    res_meta = sly.ProjectMeta(obj_classes=sly.ObjClassCollection(res_classes))
    progress = sly.Progress("Processing foregrounds", len(to_generate))
    progress_cb(api, task_id, progress)
    progress_every = max(10, len(to_generate) // 20)
    cover_img = np.zeros(res_image.shape[:2], np.int32) # size is (h, w)
    objects_area = defaultdict(lambda: defaultdict(float))
    cached_images = {} # generate objects
    for idx, class_name in enumerate(to_generate, start=1):
        if class_name not in labels:
            progress.iter_done_report()
            continue
        image_id = random.choice(list(labels[class_name].keys()))
        label: sly.Label = random.choice(labels[class_name][image_id])
        if image_id in cached_images:
            source_image = cached_images[image_id]
        else:
            image_info = image_infos[image_id]
            source_image = _get_image_using_cache(api, cache_dir, image_id, image_info)
            cached_images[image_id] = source_image
        label_img, label_mask = get_label_foreground(source_image, label)
        # sly.image.write(os.path.join(cache_dir, f"{index}_label_img.png"), label_img)
        # sly.image.write(os.path.join(cache_dir, f"{index}_label_mask.png"), label_mask)
        label_img, label_mask = aug.apply_to_foreground(label_img, label_mask)
        # sly.image.write(os.path.join(cache_dir, f"{index}_aug_label_img.png"), label_img)
        # sly.image.write(os.path.join(cache_dir, f"{index}_aug_label_mask.png"), label_mask)
        label_img, label_mask = aug.resize_foreground_to_fit_into_image(
            res_image, label_img, label_mask
        )

        # label_area = label.geometry.area
        find_place = False
        for attempt in range(3):
            origin = aug.find_origin(res_image.shape, label_mask.shape)
            geometry = sly.Bitmap(
                label_mask[:, :, 0].astype(bool),
                origin=sly.PointLocation(row=origin[1], col=origin[0]),
            )

            difference = count_visibility(
                cover_img, geometry, idx, origin[0], origin[1]
            )
            allow_placement = True
            for object_idx, diff in difference.items():
                new_area = objects_area[object_idx]["current"] - diff
                visibility_portion = new_area / objects_area[object_idx]["original"]
                if visibility_portion < visibility_threshold:
                    # sly.logger.warn(f"Object '{idx}', attempt {attempt + 1}: "
                    #                 f"visible portion ({visibility_portion}) < threshold ({visibility_threshold})")
                    allow_placement = False
                    break
            if allow_placement is True:
                find_place = True
                break
        if find_place is False:
            sly.logger.warn(
                f"Object '{idx}' is skipped: can not be placed to satisfy visibility threshold"
            )

            continue
        try:
            aug.place_fg_to_bg(label_img, label_mask, res_image, origin[0], origin[1])
            geometry.draw(cover_img, color=idx)
            for object_idx, diff in difference.items():
                objects_area[object_idx]["current"] -= diff
            current_obj_area = geometry.area
            objects_area[idx]["current"] = current_obj_area
            objects_area[idx]["original"] = current_obj_area
            res_labels.append(sly.Label(geometry, res_meta.get_obj_class(class_name)))
        except Exception as e:
            sly.logger.warn(
                f"FG placement error:: label shape: {label_img.shape}; mask shape: {label_mask.shape}",
                extra={"error": repr(e)},
            )

        progress.iter_done_report()
        if idx % progress_every == 0:
            progress_cb(api, task_id, progress)
    progress_cb(api, task_id, progress)
    res_ann = sly.Annotation(img_size=bg.shape[:2], labels=res_labels)
    # debug visualization
    # sly.image.write(os.path.join(cache_dir, "__res_img.png"), res_image)
    # res_ann.draw(res_image)
    # sly.image.write(os.path.join(cache_dir, "__res_ann.png"), res_image)
    res_meta, res_ann = rasterize.convert_to_nonoverlapping(res_meta, res_ann)
    return res_image, bg_info, res_ann, res_meta


def count_visibility(cover_img, bitmap: sly.Bitmap, idx, x, y):
    sec_h, sec_w = bitmap._data.shape
    crop = cover_img[y: y + sec_h, x: x + sec_w].copy()
    before_values, before_counts = np.unique(crop, return_counts=True)
    difference = {
        value: count for value, count in zip(before_values, before_counts) if value != 0
    }

    crop[bitmap._data] = idx
    after_values, after_counts = np.unique(crop, return_counts=True)
    for value, count in zip(after_values, after_counts):
        if value in [0, idx]:
            continue
        difference[value] -= count
        if difference[value] < 0:
            raise ValueError("Impossible difference")
        if difference[value] == 0:
            difference.pop(value)
    return difference


def convert_res_classes_to_bitmap(res_classes):
    for idx, obj_class in enumerate(res_classes):
        if obj_class.geometry_type != sly.Bitmap:
            res_classes[idx] = obj_class.clone(geometry_type=sly.Bitmap)
    return res_classes


def merge_bg_img_metas(img_proj_meta: sly.ProjectMeta, bg_proj_meta: sly.ProjectMeta):
    img_proj_metga_obj_classes_names = [obj_class.name for obj_class in img_proj_meta.obj_classes]
    new_bg_classes = []
    for bg_class in bg_proj_meta.obj_classes:
        bg_class: sly.ObjClass
        if f"{bg_class.name}-mask" in img_proj_metga_obj_classes_names:
            bg_class = bg_class.clone(name=f"{bg_class.name}-mask", geometry_type=sly.Bitmap)
        elif f"{bg_class.name}-bbox" in img_proj_metga_obj_classes_names:
            bg_class = bg_class.clone(name=f"{bg_class.name}-bbox", geometry_type=sly.Rectangle)
        else:
            bg_class = bg_class.clone(name=f"{bg_class.name}-background")
        new_bg_classes.append(bg_class)

    if new_bg_classes:
        for bg_class in new_bg_classes:
            if bg_class not in img_proj_meta.obj_classes:
                img_proj_meta = img_proj_meta.add_obj_class(bg_class)
    return img_proj_meta


def merge_bg_img_ann(img_ann: sly.Annotation, bg_ann: sly.Annotation, merged_meta: sly.ProjectMeta):
    new_labels = []
    for label in bg_ann.labels:
        obj_class = merged_meta.get_obj_class(f"{label.obj_class.name}-background")
        if obj_class is None:
            obj_class = merged_meta.get_obj_class(f"{label.obj_class.name}-mask")
        if obj_class is None:
            obj_class = merged_meta.get_obj_class(f"{label.obj_class.name}-bbox")
        if obj_class is None:
            continue
        label = label.convert(obj_class)[0]
        new_labels.append(label.clone(obj_class=obj_class, tags=label.tags))
    return img_ann.add_labels(labels=new_labels).add_tags(tags=bg_ann.img_tags)
