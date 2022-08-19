import os
import sys
from collections import defaultdict

import supervisely as sly
from supervisely.app.v1.app_service import AppService

app_root_directory = os.path.dirname(os.getcwd())
sys.path.append(app_root_directory)
sys.path.append(os.path.join(app_root_directory, "src"))
print(f"App root directory: {app_root_directory}")
sly.logger.info(f'PYTHONPATH={os.environ.get("PYTHONPATH", "")}')

# order matters
# from dotenv import load_dotenv
# load_dotenv(os.path.join(app_root_directory, "secret_debug.env"))
# load_dotenv(os.path.join(app_root_directory, "debug.env"))


app: AppService = AppService()

team_id = int(os.environ["context.teamId"])
workspace_id = int(os.environ["context.workspaceId"])
project_id = int(os.environ["modal.state.slyProjectId"])

project_info = app.public_api.project.get_info_by_id(project_id)
if project_info is None:
    raise RuntimeError(f"Project id={project_id} not found")

meta = sly.ProjectMeta.from_json(app.public_api.project.get_meta(project_id))
if len(meta.obj_classes) == 0:
    raise ValueError("Project should have at least one class")

bg_meta = None

images_info = {}
anns = {}
labels = defaultdict(lambda: defaultdict(list))

CNT_GRID_COLUMNS = 1
empty_gallery = {
    "content": {
        "projectMeta": sly.ProjectMeta().to_json(),
        "annotations": {},
        "layout": [[] for _ in range(CNT_GRID_COLUMNS)],
    },
    "previewOptions": {"enableZoom": True, "resizeOnZoom": True},
    "options": {
        "enableZoom": False,
        "syncViews": False,
        "showPreview": True,
        "selectable": False,
        "opacity": 0.5,
    },
}
