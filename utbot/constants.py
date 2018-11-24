import re
import json
import os

from beem import Steem
from beem.instance import set_shared_steem_instance
from beem.nodelist import NodeList

here = os.path.dirname(__file__)
with open(os.path.join(here, "config.json"), "r") as f:
    CONFIG = json.load(f)

# Steem config
STM = Steem(node=NodeList().get_nodes(), timeout=15)
set_shared_steem_instance(STM)

# UTOPIAN CATEGORIES
CATEGORIES_PROPERTIES = {
    "analysis": {
        "color": "#164265",
        "name": "analysis",
        "image_url": "https://i.imgsafe.org/6e/6e1ebd6655.png",
    },
    "ideas": {
        "color": "#54d2a0",
        "name": "ideas",
        "image_url": "https://i.imgsafe.org/6e/6e0c6738dc.png",
    },
    "development": {
        "color": "#000",
        "name": "development",
        "image_url": "https://i.imgsafe.org/89/8900cca3dd.png",
    },
    "bug-hunting": {
        "color": "#d9534f",
        "name": "bug-hunting",
        "image_url": "https://i.imgsafe.org/6e/6e0c5d5b89.png",
    },
    "translations": {
        "color": "#ffce3d",
        "name": "translations",
        "image_url": "https://i.imgsafe.org/6e/6e0c6a5717.png",
    },
    "graphics": {
        "color": "#f6a623",
        "name": "graphics",
        "image_url": "https://i.imgsafe.org/6e/6e0c637019.png",
    },
    "social": {
        "color": "#7ec2f3",
        "name": "social",
        "image_url": "https://i.imgsafe.org/6e/6e0c699e7f.png",
    },
    "documentation": {
        "color": "#b1b1b1",
        "name": "documentation",
        "image_url": "https://i.imgsafe.org/6e/6e0c6379e7.png",
    },
    "tutorials": {
        "color": "#782c51",
        "name": "tutorials",
        "image_url": "https://i.imgsafe.org/6e/6e0c6c2d63.png",
    },
    "video-tutorials": {
        "color": "#ec3324",
        "name": "video-tutorials",
        "image_url": "https://i.imgsafe.org/6e/6e0c6cff9f.png",
    },
    "copywriting": {
        "color": "#008080",
        "name": "copywriting",
        "image_url": "https://i.imgsafe.org/6e/6e0c5f3cd9.png",
    },
    "blog": {
        "color": "#0275d8",
        "name": "blog",
        "image_url": "https://i.imgsafe.org/6e/6e0c5c9970.png",
    },
    "iamutopian": {
        "color": "#B10DC9",
        "name": "iamutopian",
        "image_url": "https://i.imgsafe.org/6e/6e0c66aa52.png",
    },
    "anti-abuse": {
        "color": "#800000",
        "name": "anti-abuse",
        "image_url": "https://i.imgsafe.org/6e/6e0c58ea30.png",
    },
}
# alternate category names
CATEGORIES_PROPERTIES["suggestions"] = CATEGORIES_PROPERTIES["ideas"]
CATEGORIES_PROPERTIES["bughunting"] = CATEGORIES_PROPERTIES["bug-hunting"]
CATEGORIES_PROPERTIES["visibility"] = CATEGORIES_PROPERTIES["social"]
CATEGORIES_PROPERTIES["tutorial"] = CATEGORIES_PROPERTIES["tutorials"]
CATEGORIES_PROPERTIES["videotutorials"] = CATEGORIES_PROPERTIES["video-tutorials"]
CATEGORIES_PROPERTIES["videotutorial"] = CATEGORIES_PROPERTIES["video-tutorials"]
CATEGORIES_PROPERTIES["video-tutorial"] = CATEGORIES_PROPERTIES["video-tutorials"]
CATEGORIES_PROPERTIES["antiabuse"] = CATEGORIES_PROPERTIES["anti-abuse"]

# UTOPIAN TASK REQUESTS
TASKS_PROPERTIES = {}
for k, v in CATEGORIES_PROPERTIES.items():
    TASKS_PROPERTIES[f"task-{k}"] = {
        "color": v["color"],
        "name": f'task-{v["name"]}',
        "category": v["name"],
        "image_url": v["image_url"],
    }

# BOT PROPERTIES
CMD_PREFIX = CONFIG["bot_prefix"]
CMD_BOT_NAME = CONFIG["bot_name"]

# BOT COMMANDS REGEX
CMD_RE = re.compile(
    rf"""
(?P<bot_cmd>{CMD_PREFIX}{CMD_BOT_NAME})     # bot called
"""
    r"""
(?:
    (?:
        [ \t]+(?P<help>help)                # help command with preceding space
    )
    | (?:\s+(?:--)?(?:
          (?:status:?\s+?(?P<status>open|in[ ]progress|closed))                     # status [open, in progress, closed]
        | (?:bounty:?\s+?(?P<bounty>(?:\s*?\d+(?:\.\d+?)?[ ]\w+(?:\s*?,\s*?)?)+))   # bounty 00 name[, 01 name2]
        | (?:description:?\s+?"(?P<description>.+?)")     # description "text"
        | (?:note:?\s+?"(?P<note>.+?)")     # note "text"
        | (?:skills:?\s+?"(?P<skills>(?:[-_\w ]+(?:\s*?,?\s*?))+)")   # skills skillone[, skilltwo, ...]
        | (?:discord:?\s+?(?P<discord><@!\d+>|.+?[#]\d{4}))                 # <@00000000000> | username#0000
        | (?:deadline:?\s+?(?P<deadline>\d{4}-\d{2}-\d{2})(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{4})?)?) # deadline YYYY-MM-DD (considers only date)
        | (?:assignees:?\s+?"(?P<assignees>@(?:[\w\d.-]+(?:\s*?,\s*?)?)+)")  # naive regex
    );?)*
)?
""",
    flags=re.VERBOSE | re.IGNORECASE | re.MULTILINE,
)

ACCOUNTS = CONFIG["reviewers"]
UI_BASE_URL = CONFIG["steem_ui_url"]
