import os

import supervisely as sly

from dotenv import load_dotenv

ABSOLUTE_PATH = os.path.dirname(__file__)
TMP_DIR = os.path.join(ABSOLUTE_PATH, "tmp")

# Directory where temporary downloaded images will be stored.
IMAGES_DIR = os.path.join(TMP_DIR, "images")

# Path to the .env file, if the app is started from the team files.
ENV_FILE = os.path.join(ABSOLUTE_PATH, "assets.env")

STATIC_DIR = os.path.join(ABSOLUTE_PATH, "static")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

load_dotenv("local.env")
load_dotenv(os.path.expanduser("~/supervisely.env"))
api: sly.Api = sly.Api.from_env()

TEAM_ID = sly.io.env.team_id()

# Default settings for uploading primitives to Assets.
DEFAULT_TEAM_NAME = "primitives"
DEFAULT_TAG_NAME = "inference"
DEFAULT_ANNOTATION_TYPES = ["bitmap"]

# Path to the JSON file which is generated after comparsion of the teams is finished.
DIFFERENCES_JSON = os.path.join(TMP_DIR, "team_differences.json")

BATCH_SIZE = 100
GEOMETRIES = ["bitmap", "polygon", "polyline", "rectangle"]


class State:
    """Class for storing global variables across the app in one place."""

    def __init__(self):
        self.selected_team = sly.io.env.team_id()
        self.selected_workspace = sly.io.env.workspace_id()
        self.selected_project = sly.io.env.project_id(raise_not_found=False)
        self.selected_dataset = sly.io.env.dataset_id(raise_not_found=False)

        # Address of the target instance.
        self.assets_team_name = None
        self.instance = None
        self.assets_api_key = None
        # API object for the target instance, icludes API key and instance address.
        self.assets_api = None
        # If the app was SUCCESSFULLY launched from the TeamFiles.
        self.from_team_files = False


STATE = State()


def key_from_file():
    """Tries to load Target API key and the instance address from the team files."""
    try:
        # Get target.env from the team files.
        INPUT_FILE = sly.env.file(True)
        api.file.download(TEAM_ID, INPUT_FILE, ENV_FILE)
        sly.logger.info(f"Target API key file was downloaded to {ENV_FILE}.")

        # Read Target API key from the file.
        load_dotenv(ENV_FILE)
        STATE.assets_api_key = os.environ["TARGET_API_TOKEN"]
        STATE.instance = os.environ["TARGET_SERVER_ADDRESS"]

        sly.logger.info("Target API key and instance were loaded from the team files.")
    except Exception:
        sly.logger.info(
            "No file with Target API key was provided, starting in input mode."
        )
