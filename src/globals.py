import os

from collections import defaultdict

import supervisely as sly

from dotenv import load_dotenv

ABSOLUTE_PATH = os.path.dirname(__file__)
AUGS_FILE = os.path.join(ABSOLUTE_PATH, "augs.yaml")

# Local path to the .env file, if the app is started from the team files.
ENV_FILE = "assets.env"

ASSETS_ADDRESS = "https://assets.supervisely.com"
WEB_ADDRESS = "https://ecosystem.supervisely.com/primitives/assets/"
ASSETS_TEAM = "primitives"
ASSETS_TEAM_ID = 3

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))
api: sly.Api = sly.Api.from_env()

SLY_APP_DATA_DIR = sly.app.get_data_dir()
STATIC_DIR = os.path.join(SLY_APP_DATA_DIR, "static")
CACHE_DIR = os.path.join(SLY_APP_DATA_DIR, "cache")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

MAX_WORKERS = os.cpu_count() * 2

LABEL_MODES = {
    "Ignore labels": "ignore",
    "Merge with syntehtic labels": "merge",
}

TASK_TYPES = {
    "Segmentation": "segmentation",
    "Detection": "detection",
    "Instance segmentation": "instance_segmentation",
}

TASK_TOOLTIPS = {
    "segmentation": "All objects of same class on image will be merged to a single mask.",
    "detection": "Masks will be transformed to bounding boxes.",
    "instance_segmentation": "Separate mask for every object.",
}


class State:
    class Settings:
        def __init__(self):
            self.background_project_id = None

            self.use_all_datasets = None
            self.background_dataset_ids = None

            self.label_mode = None

            self.selected_classes = None
            self.augmentations = None
            self.advanced_options = None

            self.task_type = None
            self.random_colors = None

            self.use_assets = None
            self.selected_primitives = None

        def clear(self):
            self.__init__()

    class Assets:
        def __init__(self):
            self.data = {}
            self.checkboxes = {}
            self.project_ids = []
            # self.class_names = []

        def clear(self):
            self.project_ids = []
            # self.class_names = []

    def __init__(self):
        self.SETTINGS = self.Settings()
        self.ASSETS = self.Assets()

        self.selected_team = sly.io.env.team_id()
        self.selected_workspace = sly.io.env.workspace_id()
        self.selected_project = sly.io.env.project_id(raise_not_found=False)
        self.project_meta = None

        self.assets_api_key = None
        # API object for the target instance, icludes API key and instance address.
        self.assets_api = None
        # If the app was SUCCESSFULLY launched from the TeamFiles.
        self.from_team_files = False

        self.augs = None
        self.read_augs()

        self.background_image_infos = None
        self.labels = defaultdict(lambda: defaultdict(list))
        self.image_infos = {}

        self.aug_color_fg = None
        self.aug_spacial_fg = {}

        self.continue_generation = True

        self.cached_images = {}

    def get_project_meta(self):
        sly.logger.debug(
            f"Trying to get project meta for project ID: {self.selected_project}."
        )

        project_meta_json = api.project.get_meta(self.selected_project)
        self.project_meta = sly.ProjectMeta.from_json(project_meta_json)

        sly.logger.info(
            "Project meta was loaded from project and saved in the global state."
        )

    def read_augs(self):
        with open(AUGS_FILE, "r") as f:
            self.augs = f.read()

        sly.logger.info(f"Augmentations were loaded from the file: {AUGS_FILE}.")

    """
    def save_augs(self, augs):
        with open(AUGS_FILE, "w") as f:
            f.write(augs)

        sly.logger.info(f"Augmentations were saved to the file: {AUGS_FILE}.")
        self.read_augs()"""


STATE = State()


def key_from_file():
    """Tries to load Assets API key and the instance address from the team files."""
    try:
        # Get assets.env from the team files.
        INPUT_FILE = sly.env.file(True)
        api.file.download(STATE.selected_team, INPUT_FILE, ENV_FILE)
        sly.logger.info(f"Assets API key file was downloaded to {ENV_FILE}.")

        # Read Assets API key from the file.
        if os.path.exists(ENV_FILE):
            sly.logger.info(f"File {ENV_FILE} exists, reading Assets API key.")

        load_dotenv(ENV_FILE)
        STATE.assets_api_key = os.environ["ASSETS_API_TOKEN"]

        sly.logger.info("Assets API key was loaded from the team files.")
    except Exception:
        sly.logger.info(
            "No file with Assets API key was provided, starting in input mode."
        )
