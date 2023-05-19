from supervisely.app.widgets import Card, LabeledImage, Button, Container

image_preview = LabeledImage()
random_image_button = Button("New random image", icon="zmdi zmdi-refresh")

card = Card(
    "3️⃣ Random preview",
    "Preview synthetic images and labels, overlapping is handled automatically, fully covered images are skipped.",
    content=Container([random_image_button, image_preview]),
    collapsable=True,
    lock_message="Save settings on step 2️⃣.",
)
card.lock()
card.collapse()
