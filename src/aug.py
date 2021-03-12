import imgaug as ia
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage
from ast import literal_eval
import supervisely_lib as sly
import albumentations as A

aug_color_fg = None
aug_spacial_fg = None


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


name_func_spacial = {
    "Fliplr": iaa.Fliplr,
    "Flipud": iaa.Flipud,
    "Rotate": iaa.Rotate,
    #"ElasticTransformation": iaa.ElasticTransformation,
    "Resize": iaa.Resize,
}


def init_fg_augs(settings):
    init_color_augs(settings['objects']['augs']['color'])
    init_spacial_augs(settings['objects']['augs']['spacial'])


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


def init_spacial_augs(data):
    global aug_spacial_fg
    augs = []
    for key, value in data.items():
        if key == 'ElasticTransformation':
            alpha = literal_eval(value['alpha'])
            sigma = literal_eval(value['sigma'])
            augs.append(iaa.ElasticTransformation(alpha=alpha, sigma=sigma))
            continue
        if key not in name_func_spacial:
            sly.logger.warn(f"Aug {key} not found, skipped")
            continue

        parsed_value = value
        if type(value) is str:
            parsed_value = literal_eval(value)

        if key == 'Rotate':
            a = iaa.Rotate(rotate=parsed_value, fit_output=True)
        else:
            a = name_func_spacial[key](parsed_value)
        augs.append(a)
    aug_spacial_fg = iaa.Sequential(augs, random_order=True)


def apply_to_foreground(image, mask):
    if image.shape[:2] != mask.shape[:2]:
        raise ValueError(f"Image ({image.shape}) and mask ({mask.shape}) have different resolutions")

    # apply color augs
    augmented = aug_color_fg(image=image, mask=mask)
    image_aug = augmented['image']
    mask_aug = augmented['mask']

    # apply spacial augs
    segmap = SegmentationMapsOnImage(mask_aug, shape=mask_aug.shape)
    image_aug, segmap_aug = aug_spacial_fg(image=image_aug, segmentation_maps=segmap)
    mask_aug = segmap_aug.get_arr()
    return image_aug, mask_aug