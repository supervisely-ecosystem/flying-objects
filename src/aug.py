import albumentations as A
import cv2

transform_fg = None


def init_fg_augs(settings):
    global transform_fg
    augs = []

    color_augs = settings['objects']['augs']['color']
    if color_augs['RandomBrightnessContrast'] is True:
        augs.append(A.RandomBrightnessContrast())
    if color_augs['RandomGamma'] is True:
        augs.append(A.RandomGamma())
    if color_augs['HueSaturationValue'] is True:
        augs.append(A.HueSaturationValue())
    if color_augs['Blur'] is True:
        augs.append(A.Blur())

    spacial_augs = settings['objects']['augs']['spacial']
    if spacial_augs['VerticalFlip'] is True:
        augs.append(A.VerticalFlip())
    if spacial_augs['HorizontalFlip'] is True:
        augs.append(A.HorizontalFlip())
    if 'Rotate' in spacial_augs:
        augs.append(A.Rotate(limit=spacial_augs['Rotate'],
                             interpolation=cv2.INTER_NEAREST,
                             border_mode=cv2.BORDER_CONSTANT,
                             value=0, mask_value=0)
                    )
    if 'ElasticTransform' in spacial_augs:
        alpha = spacial_augs['ElasticTransform']
        augs.append(A.ElasticTransform(alpha=alpha, sigma=alpha * 0.05, alpha_affine=alpha * 0.03))

    _alpha = 300
    transform_fg = A.Compose(augs)


def apply_to_foreground(image, mask):
    augmented = transform_fg(image=image, mask=mask)
    image_aug = augmented['image']
    mask_aug = augmented['mask']
    return image_aug, mask_aug