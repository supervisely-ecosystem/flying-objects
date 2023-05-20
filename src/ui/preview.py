import os
import secrets

from random import choice, randint, shuffle
from collections import defaultdict

from supervisely.app.widgets import Card, LabeledImage, Button, Container, Grid, Empty

import supervisely as sly
import numpy as np

import src.globals as g
import src.aug as aug
import src.rasterize as rasterize
from src.postprocess import postprocess, highlight_instances

image_preview = LabeledImage()
image_preview.hide()
image_preview_grid = Grid([Empty(), image_preview, Empty()], columns=3)
random_image_button = Button("New random image", icon="zmdi zmdi-refresh")

card = Card(
    "3️⃣ Random preview",
    "Preview synthetic images and labels, overlapping is handled automatically, fully covered images are skipped.",
    content=Container([random_image_button, image_preview_grid]),
    collapsable=True,
    lock_message="Save settings on step 2️⃣.",
)
card.lock()
card.collapse()


@random_image_button.click
def preview():
    random_image_button.loading = True

    image, ann, res_meta = synthesize()
    res_meta, ann = postprocess(ann, res_meta, sly.ProjectMeta())
    if (
        g.STATE.SETTINGS.task_type == "instance_segmentation"
        and g.STATE.SETTINGS.random_colors is True
    ):
        res_meta, ann = highlight_instances(res_meta, ann)

    sly.logger.info("Successfully generated image and annotation.")

    random_image_name = f"{secrets.token_hex(10)}.png"

    image_path = os.path.join(g.STATIC_DIR, random_image_name)

    sly.image.write(image_path, image)

    sly.logger.info(f"Succesfully saved image to static dir with path {image_path}.")

    image_preview.set(
        image_url=os.path.join("static", random_image_name),
        ann=ann,
        title=random_image_name,
    )
    image_preview.show()

    sly.logger.debug("Updated image in prevew widget.")

    random_image_button.loading = False


def synthesize():
    aug.init_fg_augs()

    visibility_threshold = g.STATE.SETTINGS.augmentations["objects"].get(
        "visibility", 0.8
    )

    background_image_info = choice(g.STATE.background_image_infos)
    background_image_np = g.api.image.download_np(background_image_info.id)

    sly.logger.debug(
        f"Successfully downloaded background image with id {background_image_info.id} "
        f"and shape {background_image_np.shape} as numpy array."
    )

    if g.STATE.SETTINGS.use_assets:
        class_names = g.STATE.ASSETS.class_names

    else:
        class_names = g.STATE.SETTINGS.selected_classes

    res_image = background_image_np.copy()

    res_classes = []
    to_generate = []
    for class_name in class_names:
        original_class = g.STATE.project_meta.get_obj_class(class_name)
        res_classes.append(original_class.clone(geometry_type=sly.Bitmap))

        count = randint(*g.STATE.SETTINGS.augmentations["objects"]["count"])
        for i in range(count):
            to_generate.append(class_name)

    shuffle(to_generate)

    sly.logger.debug(f"Prepared list with {len(to_generate)} objects to generate.")

    # Debug code, because projects on assets have non unique classes and should be fixed.

    debug_names_in_res_classes = [obj_class.name for obj_class in res_classes]
    print("DEBUG PRINT OF NAMES IN RES CLASSES:", debug_names_in_res_classes)
    print(
        "LIST OF DUPLICATE NAMES:",
        [
            name
            for name in debug_names_in_res_classes
            if debug_names_in_res_classes.count(name) > 1
        ],
    )
    if len(debug_names_in_res_classes) != len(set(debug_names_in_res_classes)):
        raise RuntimeError("Non unique names in res classes.")

    res_meta = sly.ProjectMeta(obj_classes=sly.ObjClassCollection(res_classes))

    res_labels = []

    if g.STATE.SETTINGS.label_mode == "merge":
        sly.logger.info("Merge mode, will handle labels from background project.")

        background_project_meta_json = g.api.project.get_meta(
            g.STATE.SETTINGS.background_project_id
        )
        background_project_meta = sly.ProjectMeta.from_json(
            background_project_meta_json
        )

        sly.logger.debug(
            f"Successfully downloaded meta of background project with id "
            f"{g.STATE.SETTINGS.background_project_id} and converted it to ProjectMeta."
        )
        print("Before receiving background ann json.")
        background_ann_json = g.api.annotation.download_json(background_image_info.id)

        print("After receiving background ann json.")
        background_ann = sly.Annotation.from_json(
            background_ann_json, background_project_meta
        )
        print("After converting background ann json to annotation.")

        for label in background_ann.labels:
            obj_class = res_meta.get_obj_class(label.obj_class.name)
            if obj_class is None:
                # The class wasn't selected in the project settings.
                continue
            if isinstance(label.geometry, sly.Bitmap):
                res_labels.append(label.clone(obj_class=obj_class))
                continue
            if isinstance(label.geometry, sly.Polygon):
                res_labels.extend(label.convert(new_obj_class=obj_class))
                continue

        sly.logger.debug(
            f"Successfully added {len(res_labels)} labels from background project."
        )

    sly.logger.debug(f"Starting iteration over {len(to_generate)} objects to generate.")

    cover_img = np.zeros(res_image.shape[:2], np.int32)
    objects_area = defaultdict(lambda: defaultdict(float))

    for idx, class_name in enumerate(to_generate, start=1):
        if class_name not in g.STATE.labels:
            sly.logger.debug(
                f"Class {class_name} can't be found in global state labels and will be skipped."
            )
            continue

        image_id = choice(list(g.STATE.labels[class_name].keys()))
        label = choice(g.STATE.labels[class_name][image_id])

        if g.STATE.SETTINGS.use_assets:
            api = g.STATE.assets_api
            sly.logger.debug("The app in assets mode, will use assets api.")
        else:
            api = g.api
            sly.logger.debug("The app in project mode, will use project api.")

        # image_info = g.STATE.image_infos[image_id] # For caching later.
        image_np = api.image.download_np(image_id)

        label_img, label_mask = get_label_foreground(image_np, label)

        sly.logger.debug(f"Generated label foreground for image {image_id}.")

        label_img, label_mask = aug.apply_to_foreground(label_img, label_mask)

        sly.logger.debug(f"Applied foreground augmentations for image {image_id}.")

        label_img, label_mask = aug.resize_foreground_to_fit_into_image(
            res_image, label_img, label_mask
        )

        sly.logger.debug("Resized foreground to fit into background image.")

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
                    allow_placement = False
                    break

            if allow_placement is True:
                find_place = True
                break
            else:
                continue

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
    res_ann = sly.Annotation(img_size=background_image_np.shape[:2], labels=res_labels)
    res_meta, res_ann = rasterize.convert_to_nonoverlapping(res_meta, res_ann)

    sly.logger.info("Synthetic image generation is finished successfully.")

    return res_image, res_ann, res_meta


def get_label_foreground(image_np, label):
    bbox = label.geometry.to_bbox()
    img_crop = sly.image.crop(image_np, bbox)
    new_label = label.translate(drow=-bbox.top, dcol=-bbox.left)
    h, w = img_crop.shape[0], img_crop.shape[1]
    mask = np.zeros((h, w, 3), np.uint8)
    new_label.draw(mask, [255, 255, 255])
    return img_crop, mask


def count_visibility(cover_img, bitmap: sly.Bitmap, idx, x, y):
    sec_h, sec_w = bitmap._data.shape
    crop = cover_img[y : y + sec_h, x : x + sec_w].copy()
    before_values, before_counts = np.unique(crop, return_counts=True)
    difference = {}
    for value, count in zip(before_values, before_counts):
        if value == 0:
            continue
        difference[value] = count

    crop[bitmap._data] = idx
    after_values, after_counts = np.unique(crop, return_counts=True)
    for value, count in zip(after_values, after_counts):
        if value == 0 or value == idx:
            continue
        difference[value] -= count
        if difference[value] < 0:
            raise ValueError("Impossible difference")
        if difference[value] == 0:
            difference.pop(value)

    return difference
