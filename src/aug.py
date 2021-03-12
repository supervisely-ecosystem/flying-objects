import imgaug as ia
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage

transform_fg = None


name_func_color = {
    "GaussianNoise": iaa.imgcorruptlike.GaussianNoise,
    "GaussianBlur": iaa.imgcorruptlike.GaussianBlur,
    "GammaContrast": iaa.GammaContrast,
    "Contrast": iaa.imgcorruptlike.Contrast,
    "Brightness": iaa.imgcorruptlike.Brightness
}

name_func_spacial = {
    "Fliplr": iaa.Fliplr,
    "Flipud": iaa.Flipud,
    "Rotate": iaa.Rotate,
    "ElasticTransformation": iaa.ElasticTransformation,
    "Resize": iaa.Resize
}


def init_fg_augs(settings):
    global transform_fg
    augs = []

    color_augs = settings['objects']['augs']['color']
    for key, value in color_augs.items():
        augs.append(name_func_color[key](value))

    spacial_augs = settings['objects']['augs']['spacial']
    for key, value in spacial_augs.items():
        augs.append(name_func_spacial[key](value))

    transform_fg = iaa.Sequential(augs, random_order=True)


def apply_to_foreground(image, mask):
    segmap = SegmentationMapsOnImage(mask, shape=mask.shape)
    image_aug, segmap_aug = transform_fg(image=image, segmentation_maps=segmap)
    mask_aug = segmap_aug.get_arr()
    return image_aug, mask_aug