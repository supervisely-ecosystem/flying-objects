import supervisely as sly

from supervisely.app.widgets import Container

import src.globals as g
import src.ui.input as input
import src.ui.settings as settings
import src.ui.preview as preview
import src.ui.output as output

layout = Container(widgets=[input.card, settings.card, preview.card, output.card])

app = sly.Application(layout=layout, static_dir=g.STATIC_DIR, hot_reload=True)
