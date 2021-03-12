import imgaug as ia
import imgaug.augmenters as iaa
from imgaug.augmentables.segmaps import SegmentationMapsOnImage
from ast import literal_eval
import supervisely_lib as sly

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
    #"ElasticTransformation": iaa.ElasticTransformation,
    "Resize": iaa.Resize
}


def init_fg_augs(settings):
    def map_name_to_func(data, name_func, result):
        for key, value in data.items():
            if key == 'ElasticTransformation':
                alpha = literal_eval(value['alpha'])
                sigma = literal_eval(value['sigma'])
                result.append(iaa.ElasticTransformation(alpha=alpha, sigma=sigma))
                continue
            if key not in name_func:
                sly.logger.warn(f"Aug {key} not found, skipped")
            parsed_value = value
            if type(value) is str:
                parsed_value = literal_eval(value)

            if key == 'Rotate':
                a = iaa.Rotate(rotate=parsed_value, fit_output=True)
            else:
                a = name_func[key](parsed_value)
            result.append(a)

    global transform_fg
    augs = []

    map_name_to_func(settings['objects']['augs']['color'], name_func_color, augs)
    map_name_to_func(settings['objects']['augs']['spacial'], name_func_spacial, augs)
    transform_fg = iaa.Sequential(augs, random_order=True)


def apply_to_foreground(image, mask):
    if image.shape[:2] != mask.shape[:2]:
        raise ValueError(f"Image ({image.shape}) and mask ({mask.shape}) have different resolutions")
    #h, w = image.shape[0], image.shape[1]
    #if h < 32 or w < 32:
        # cover case - the lower limit that the wrapped imagecorruptions functions use
    #    hard_resize = iaa.Resize({"shorter-side": 32, "longer-side": "keep-aspect-ratio"})
    #aug = iaa.Resize({"shorter-side": 224, "longer-side": "keep-aspect-ratio"})


    segmap = SegmentationMapsOnImage(mask, shape=mask.shape)
    image_aug, segmap_aug = transform_fg(image=image, segmentation_maps=segmap)
    mask_aug = segmap_aug.get_arr()
    return image_aug, mask_aug