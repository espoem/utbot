import typing

import logging
import logging.config
import os
import json

from constants import CATEGORIES_PROPERTIES, CMD_RE, TASKS_PROPERTIES, UI_BASE_URL

logger = logging.getLogger(__name__)


def parse_command(cmd_str: str) -> dict:
    """Parses command in an arbitrary string.

    :param cmd_str: text
    :type cmd_str: str
    :return: dictionary with parsed commands and arguments
    :rtype: dict
    """
    found = CMD_RE.search(cmd_str)
    if not found:
        return None
    logger.info("Command parsed. %s", found.groupdict())
    return found.groupdict()


def build_comment_link(comment: dict) -> str:
    return f'{UI_BASE_URL}{comment["url"]}'


def build_steem_account_link(username: str) -> str:
    return f"{UI_BASE_URL}/@{username}"


def is_utopian_contribution(comment: dict) -> bool:
    tags = comment["tags"]
    has_utopian_tag = "utopian-io" in tags
    has_utopian_category = not set(CATEGORIES_PROPERTIES.keys()).isdisjoint(set(tags))
    return has_utopian_tag and has_utopian_category


def is_utopian_task_request(comment: dict) -> bool:
    tags = comment["tags"]
    has_utopian_tag = "utopian-io" in tags
    has_utopian_category = not set(TASKS_PROPERTIES.keys()).isdisjoint(set(tags))
    return has_utopian_tag and has_utopian_category


def get_category(comment: dict, categories: typing.Collection) -> str:
    for tag in comment["tags"]:
        if tag in categories:
            return tag
    return None


def normalize_str(str_line: str) -> str:
    items = str_line.split(",")
    items = [a.strip() for a in items if a]
    return ", ".join(items)


def accounts_str_to_md_links(str_line: str) -> str:
    items = str_line.split(",")
    items = [
        f"[{name.strip(' @')}]({build_steem_account_link(name.strip(' @'))})"
        for name in items
        if name
    ]
    return ", ".join(items)


def setup_logger():
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, "logger_config.json"), "r") as log_config:
        config_dict = json.load(log_config)

    logging.config.dictConfig(config_dict)
