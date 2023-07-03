import cv2
import random
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage
from ast import literal_eval
import supervisely as sly
import albumentations as A

import src.globals as g


name_func_color = {
    "RandomBrightnessContrast": A.RandomBrightnessContrast,
    "CLAHE": A.CLAHE,
    "Blur": A.Blur,
}


name_func_spacial = {
    "Fliplr": iaa.Fliplr,
    "Flipud": iaa.Flipud,
    "Rotate": iaa.Rotate,
    "Resize": iaa.Resize,
}


def init_fg_augs():
    sly.logger.debug("Initializing foreground augmentations.")

    settings = g.STATE.SETTINGS.augmentations
    init_color_augs(settings["objects"]["augs"]["color"])

    sly.logger.debug(
        "Will try to initialize spacial augs for each selected class (or primitive)."
    )
    if g.STATE.SETTINGS.use_assets:
        # If working with assets, the selected primitives is a dictionary with workspace names as keys, and lists of
        # primitive names as values.
        class_names = g.STATE.ASSETS.class_names

    else:
        # If working with Supervisely project, the selected classes is a list of class names.
        class_names = g.STATE.SETTINGS.selected_classes

    sly.logger.debug(
        f"Prepared list of class names for spacial augs for each class: {class_names}"
    )

    base_spacial_augs = settings["objects"]["augs"]["spacial"]

    for class_name in class_names:
        data = base_spacial_augs.copy()

        if g.STATE.SETTINGS.advanced_options:
            if g.STATE.SETTINGS.use_assets:
                class_name_options = class_name.replace("_mask", "").replace("_", " ")
                try:
                    data["Resize"] = g.STATE.SETTINGS.advanced_options["options"][
                        "resizes"
                    ][class_name_options]
                except KeyError:
                    sly.logger.warning(
                        f"Can't find class with name {class_name_options} in "
                        "advanced options, will try to capitalize it."
                    )
                    data["Resize"] = g.STATE.SETTINGS.advanced_options["options"][
                        "resizes"
                    ][class_name_options.capitalize()]
            else:
                data["Resize"] = g.STATE.SETTINGS.advanced_options["options"][
                    "resizes"
                ][class_name]

        init_spacial_augs(class_name, data)

    sly.logger.debug("Foreground augmentations initialized.")


def init_color_augs(data):
    augs = []
    for key, value in data.items():
        for key, value in data.items():
            if key not in name_func_color:
                sly.logger.warn(f"Aug {key} not found, skipped")
                continue
        augs.append(name_func_color[key]())
    g.STATE.aug_color_fg = A.Compose(augs)

    sly.logger.debug("Foreground color augmentations initialized.")


def init_spacial_augs(class_name, data):
    augs = []
    for key, value in data.items():
        if key == "ElasticTransformation":
            alpha = literal_eval(value["alpha"])
            sigma = literal_eval(value["sigma"])
            augs.append(iaa.ElasticTransformation(alpha=alpha, sigma=sigma))
            continue
        if key not in name_func_spacial:
            sly.logger.warn(f"Aug {key} not found, skipped")
            continue

        parsed_value = value
        if type(value) is str:
            parsed_value = literal_eval(value)

        if key == "Rotate":
            a = iaa.Rotate(rotate=parsed_value, fit_output=True)
        else:
            a = name_func_spacial[key](parsed_value)
        augs.append(a)
    g.STATE.aug_spacial_fg[class_name] = iaa.Sequential(augs, random_order=True)

    sly.logger.debug("Foreground spacial augmentations initialized.")


def apply_to_foreground(image, mask, class_name):
    if image.shape[:2] != mask.shape[:2]:
        raise ValueError(
            f"Image ({image.shape}) and mask ({mask.shape}) have different resolutions"
        )

    # apply color augs
    augmented = g.STATE.aug_color_fg(image=image, mask=mask)
    image_aug = augmented["image"]
    mask_aug = augmented["mask"]

    # apply spacial augs
    segmap = SegmentationMapsOnImage(mask_aug, shape=mask_aug.shape)
    image_aug, segmap_aug = g.STATE.aug_spacial_fg[class_name](
        image=image_aug, segmentation_maps=segmap
    )
    mask_aug = segmap_aug.get_arr()
    return image_aug, mask_aug


def find_origin(image_shape, mask_shape):
    mh, mw = mask_shape[:2]
    ih, iw = image_shape[:2]
    if mh > ih or mw > iw:
        raise NotImplementedError("Mask is bigger that background image")

    x = random.randint(0, iw - mw)
    y = random.randint(0, ih - mh)
    return (x, y)


def resize_foreground_to_fit_into_image(dest_image, image, mask):
    img_h, img_w, _ = dest_image.shape
    mask_h, mask_w, _ = mask.shape

    settings = None
    if mask_h > img_h:
        settings = {"height": img_h, "width": "keep-aspect-ratio"}
    if mask_w > img_w and mask_w / img_w > mask_h / img_h:
        settings = {"height": "keep-aspect-ratio", "width": img_w}

    if settings is not None:
        aug = iaa.Resize(settings)
        segmap = SegmentationMapsOnImage(mask, shape=mask.shape)
        image_aug, segmap_aug = aug(image=image, segmentation_maps=segmap)
        mask_aug = segmap_aug.get_arr()
        return image_aug, mask_aug
    else:
        return image, mask


def place_fg_to_bg(fg, fg_mask, bg, x, y):
    sec_h, sec_w, _ = fg.shape
    secondary_object = cv2.bitwise_and(fg, fg_mask)
    secondary_bg = 255 - fg_mask
    bg[y : y + sec_h, x : x + sec_w, :] = (
        cv2.bitwise_and(bg[y : y + sec_h, x : x + sec_w, :], secondary_bg)
        + secondary_object
    )
