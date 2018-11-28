import json
import logging
import logging.config
import time
import typing

from beem.comment import Comment

from constants import (
    BOT_NAME,
    BOT_PREFIX,
    BOT_REPO_URL,
    CATEGORIES_PROPERTIES,
    CMD_RE,
    MSG_TASK_EXAMPLE_MULT_LINES,
    MSG_TASK_EXAMPLE_ONE_LINE,
    TASKS_PROPERTIES,
    UI_BASE_URL,
)

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


def build_help_message():
    """Creates a simple help message with a link to the github repository with details.
    Contains an example of bot calling.

    :return: Help message
    """
    msg_parts = [
        "Hi, you called for help. Brief examples of the bot calls are included below. "
        "You can read about the parameters in the bot [description]({bot_docs}).",
        "<hr/>",
        f"```\n{MSG_TASK_EXAMPLE_ONE_LINE}\n```",
        "<hr/>",
        f"```\n{MSG_TASK_EXAMPLE_MULT_LINES}\n```",
    ]
    msg = "\n\n".join(msg_parts).format(
        prefix=BOT_PREFIX, bot_name=BOT_NAME, bot_docs=BOT_REPO_URL
    )

    return msg


def build_missing_status_message():
    """Creates a notice that status parameter was not included.
    """
    msg_parts = [
        f"Hello, we detected that you wanted to call {BOT_NAME} without defining the current "
        f"status of the task. Please read the bot's [description]({BOT_REPO_URL}) "
        "to know about the bot valid parameters."
    ]
    msg = "\n\n".join(msg_parts)
    return msg


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
            break
        except:
            time.sleep(3)
            retry -= 1
        else:
            break
