import supervisely as sly

from supervisely.app.widgets import Container

import src.globals as g
import src.ui.input as input
import src.ui.keys as keys

layout = Container(widgets=[input.card, keys.card])

app = sly.Application(layout=layout, static_dir=g.STATIC_DIR)
