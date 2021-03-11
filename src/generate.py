import supervisely_lib as sly
import random
import yaml
import numpy as np
import os

bg_project_id = None
bg_datasets = None
bg_images = None

#@TODO: only for debug
vis_dir = "../images"
sly.fs.mkdir(vis_dir)


def update_bg_images(api, state):
    global bg_project_id, bg_datasets, bg_images

    cur_bg_project_id = state["bgProjectId"]

    cur_bg_datasets = state["bgDatasets"]
    if state["allDatasets"] is True:
        datasets_info = api.dataset.get_list(cur_bg_project_id)
        cur_bg_datasets = [info.name for info in datasets_info]

    if bg_project_id is not None and bg_datasets is not None and bg_images is not None and \
       cur_bg_project_id == bg_project_id and set(cur_bg_datasets) == set(bg_datasets):
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


def synthesize(api: sly.Api, state, project_info, meta, image_infos, anns, labels, bg_images):
    augs = yaml.safe_load(state["augs"])
    classes = state["selectedClasses"]

    bg_info = random.choice(bg_images)
    bg = api.image.download_np(bg_info.id)
    sly.logger.debug(f"BG shape: {bg.shape}")

    # sequence of objects that will be generated
    to_generate = []
    for class_name in classes:
        count_range = augs["objects"]["count"]
        count = random.randint(*count_range)
        for i in range(count):
            to_generate.append(class_name)
    random.shuffle(to_generate)

    # generate objects
    for class_name in to_generate:
        if class_name not in labels:
            continue
        image_ids = list(labels[class_name].keys())
        image_id = random.choice(image_ids)
        label: sly.Label = random.choice(labels[class_name][image_id])
        bbox = label.geometry.to_bbox()

        fg = api.image.download_np(image_id)

        # crop object and image
        object_crop = sly.image.crop(fg, bbox)
        new_label = label.translate(drow=-bbox.top, dcol=-bbox.left)
        h, w = object_crop.shape[0], object_crop.shape[1]
        mask = np.zeros((h, w, 3), np.uint8)
        new_label.draw(mask, [255, 255, 255])


        sly.image.write(os.path.join(vis_dir, "obj.png"), mask)

    pass
