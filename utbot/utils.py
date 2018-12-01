import json
import logging
import logging.config
import time
import typing

from beem.comment import Comment

from constants import (
    CATEGORIES_PROPERTIES,
    CMD_RE,
    TASKS_PROPERTIES,
    UI_BASE_URL,
)

logger = logging.getLogger(__name__)


def parse_command(cmd_str: str) -> typing.Optional[dict]:
    """Parses command in an arbitrary string.

    :param cmd_str: text
    :type cmd_str: str
    :return: dictionary with parsed commands and arguments
    :rtype: dict
    """
    found = CMD_RE.search(cmd_str)
    if not found:
        return None
    found = found.groupdict()
    parsed_cmd = {
        "help": found.get("help"),
        "status": found.get("status"),
        "bounty": [x.strip().upper() for x in found["bounty"].split(",")] if found.get("bounty") else None,
        "description": found["description"].strip() if found.get("description") else None,
        "note": found["note"].strip() if found.get("note") else None,
        "skills": [s.strip() for s in found["skills"].split(",") if s.strip()] if found.get("skills") else None,
        "discord": found.get("discord"),
        "deadline": found.get("deadline"),
        "assignees": [a.strip("@ ") for a in found["assignees"].split(',') if a.strip("@ ")] if found.get("assignees") else None
    }
    logger.info("Command parsed. %s", parsed_cmd)
    return parsed_cmd


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


def accounts_str_to_md_links(str_line: str) -> str:
    """

    :param str_line:
    :return:
    """
    items = str_line.split(",")
    items = [
        f"[{name.strip(' @')}]({build_steem_account_link(name.strip(' @'))})"
        for name in items
        if name
    ]
    return ", ".join(items)


def setup_logger(json_conf_fp: str):
    """Sets logger.

    :param json_conf_fp: Path to a json configuration file
    :type json_conf_fp: str
    """
    with open(json_conf_fp, "r") as log_config:
        config_dict = json.load(log_config)

    logging.config.dictConfig(config_dict)


def infinite_loop(func, seconds, *args, **kwargs):
    """Runs a function in a loop with a defined waiting time between loops.

    :param func: Callable function to run infinitely with a delay between loops
    :param seconds: Seconds to wait
    :param args: Args for func
    :param kwargs: Kwargs for func
    """
    while True:
        func(*args, **kwargs)
        time.sleep(seconds)


def reply_message(parent_comment: Comment, message: str, account: str, retry: int = 3):
    """Replies to a comment with a specific message.

    :param parent_comment: Parent comment to reply to
    :type parent_comment: Comment
    :param message: Message content
    :type message: str
    :param account: Author of the reply
    :type account: str
    :param retry: Number of retries, defaults to 3
    :param retry: int, optional
    """
    while retry > 0:
        try:
            parent_comment.reply(body=message, author=account)
        except ValueError:
            logger.error("No Steem account provided. Can't reply on Steem.")
            return False
        except:
            time.sleep(3)
            retry -= 1
        else:
            return True
    return False


def get_author_perm_from_url(url: str):
    """Gets author and permlink from a URL link.

    :param url: URL
    :type url: str
    :return: tuple with author and permlink
    :rtype: tuple
    """
    if "@" not in url:
        return None
    parts = url.split("@")[1]
    parts = parts.split("/")
    return parts[0], parts[1].split("#")[0]


def replied_to_comment(comment: Comment, account: str) -> typing.Optional[Comment]:
    for reply in comment.get_replies():
        if reply["author"] == account:
            return reply
    return None
