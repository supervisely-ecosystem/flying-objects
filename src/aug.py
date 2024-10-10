import cv2
import random
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage
from ast import literal_eval
import numpy as np
import supervisely as sly
import albumentations as A
import globals as g

aug_color_fg = None
aug_spatial_fg = None


# imgaug
# name_func_color = {
#     "GaussianNoise": iaa.imgcorruptlike.GaussianNoise,
#     "GaussianBlur": iaa.imgcorruptlike.GaussianBlur,
#     "GammaContrast": iaa.GammaContrast,
#     "Contrast": iaa.imgcorruptlike.Contrast,
#     "Brightness": iaa.imgcorruptlike.Brightness
# }

name_func_color = {
    "RandomBrightnessContrast": A.RandomBrightnessContrast,
    "CLAHE": A.CLAHE,
    "Blur": A.Blur,
}


name_func_spatial = {
    "Fliplr": iaa.Fliplr,
    "Flipud": iaa.Flipud,
    "Rotate": iaa.Rotate,
    # "ElasticTransformation": iaa.ElasticTransformation,
    "Resize": iaa.Resize,
}


def init_fg_augs(settings):
    init_color_augs(settings["objects"]["augs"]["color"])
    init_spatial_augs(settings["objects"]["augs"]["spatial"])


def init_color_augs(data):
    global aug_color_fg
    augs = []
    for key, value in data.items():
        for key, value in data.items():
            if key not in name_func_color:
                sly.logger.warn(f"Aug {key} not found, skipped")
                continue
        augs.append(name_func_color[key]())
    aug_color_fg = A.Compose(augs)


def init_spatial_augs(data):
    global aug_spatial_fg
    augs = []
    for key, value in data.items():
        if key == "ElasticTransformation":
            alpha = literal_eval(value["alpha"])
            sigma = literal_eval(value["sigma"])
            augs.append(iaa.ElasticTransformation(alpha=alpha, sigma=sigma))
            continue
        if key not in name_func_spatial:
            sly.logger.warn(f"Aug {key} not found, skipped")
            continue

        parsed_value = value

        if key == "Resize" and isinstance(parsed_value, dict):
            g.use_exact_resize = True
            g.exact_resize_values = convert_to_tuple(parsed_value)
            continue

        if type(value) is str:
            parsed_value = literal_eval(value)

        if key == "Rotate":
            a = iaa.Rotate(rotate=parsed_value, fit_output=True)
        else:
            if any([not(value > 0) for value in parsed_value]):
                sly.logger.warn("Cannot resize image to 0% of its original size, skipping")
                continue
            a = name_func_spatial[key](parsed_value)
        augs.append(a)
    aug_spatial_fg = iaa.Sequential(augs, random_order=True)


def convert_to_tuple(value):
    def convert(val):
        if val == "keep-aspect-ratio":
            return val
        return tuple(map(int, val.strip("()").split(",")))
    return {key: convert(val) for key, val in value.items()}


def apply_to_foreground(image, mask):
    if image.shape[:2] != mask.shape[:2]:
        raise ValueError(
            f"Image ({image.shape}) and mask ({mask.shape}) have different resolutions"
        )

    # apply color augs
    augmented = aug_color_fg(image=image, mask=mask)
    image_aug = augmented["image"]
    mask_aug = augmented["mask"]

    # apply spatial augs
    segmap = SegmentationMapsOnImage(mask_aug, shape=mask_aug.shape)
    image_aug, segmap_aug = aug_spatial_fg(image=image_aug, segmentation_maps=segmap)
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

    if g.use_exact_resize:
        settings = g.exact_resize_values
        height = settings["height"]
        width = settings["width"]

        if height != "keep-aspect-ratio":
            height = (min(height[0], img_h), min(height[1], img_h))
        if width != "keep-aspect-ratio":
            width = (min(width[0], img_w), min(width[1], img_w))

        # Ensure that the mask fits into the image
        settings = {"height": height, "width": width}

    else:
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


def place_fg_to_bg(
    fg: np.ndarray,
    fg_mask: np.ndarray,
    bg: np.ndarray,
    x: int,
    y: int,
    edge_smoothing_ksize: int = 0,
    opacity: float = 1.0,
):
    sec_h, sec_w, _ = fg.shape
    bg_crop = bg[y : y + sec_h, x : x + sec_w, :]

    # Blur the edges of the mask
    if edge_smoothing_ksize > 0:
        if edge_smoothing_ksize % 2 == 0:
            edge_smoothing_ksize += 1  # kernel size must be an odd number
        fg_mask = cv2.GaussianBlur(
            fg_mask, (edge_smoothing_ksize, edge_smoothing_ksize), 0
        )

    # Normalize to [0, 1] and apply opacity
    fg_mask = fg_mask / 255.0 * opacity

    # Blend the images
    combined_crop = (fg * fg_mask) + (bg_crop * (1 - fg_mask))

    bg[y : y + sec_h, x : x + sec_w, :] = combined_crop
