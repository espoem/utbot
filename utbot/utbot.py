import queue
import time
from queue import Queue
from threading import Thread
import logging

import beem
from beem.account import Account
from beem.blockchain import Blockchain
from beem.comment import Comment
from discord_webhook import DiscordEmbed, DiscordWebhook

from constants import (
    ACCOUNTS,
    MSG_TASK_EXAMPLE_MULT_LINES,
    MSG_TASK_EXAMPLE_ONE_LINE,
    TASKS_PROPERTIES,
    UI_BASE_URL,
    BOT_PREFIX,
    BOT_NAME,
    BOT_REPO_URL,
    ACCOUNT,
    DISCORD_WEBHOOK_TASKS,
)
from utils import (
    accounts_str_to_md_links,
    build_comment_link,
    get_category,
    is_utopian_task_request,
    normalize_str,
    parse_command,
    setup_logger,
)

# Queue
QUEUE_COMMENTS = Queue(maxsize=0)

# Logger
logger = logging.getLogger(__name__)


def build_discord_tr_embed(comment: dict, cmds_args: dict) -> DiscordEmbed:
    """Creates a Discord embed for a Utopian task request.

    :param comment: Steem root post with task request
    :type comment: dict
    :param cmds_args: Parsed bot commands and arguments
    :type cmds_args: dict
    """
    category = get_category(comment, TASKS_PROPERTIES)
    color = 0
    type_ = None
    thumbnail = None
    if category is not None:
        color = int(TASKS_PROPERTIES[category]["color"][1:], 16)
        type_ = TASKS_PROPERTIES[category]["category"]
        thumbnail = TASKS_PROPERTIES[category]["image_url"]

    title = f'{comment["title"]}'
    description_parts = []
    if cmds_args.get("description") is not None:
        description_parts.append(cmds_args["description"].strip())
    # description_parts.append(
    #     f'*You can read [here]({build_comment_link(comment)}) the whole task by **{comment["author"]}**.*'
    # )

    description = "\n\n".join(description_parts)
    embed = DiscordEmbed(title=title, description=description)
    author = Account(comment["author"])
    embed.set_author(
        name=author.name,
        url=f"{UI_BASE_URL}/@{author.name}",
        icon_url=author.profile.get("profile_image"),
    )
    embed.set_color(color)
    embed.set_footer(text="Verified by Utopian.io team")
    embed.set_thumbnail(url=thumbnail)
    embed.set_timestamp()

    if type_ is not None:
        embed.add_embed_field(name="Task Type", value=type_.upper(), inline=True)

    status = None
    if cmds_args.get("status") is not None:
        status = cmds_args["status"]
        embed.add_embed_field(name="Status", value=status.upper(), inline=True)

    if status and status.upper() == "CLOSED":
        return embed

    if cmds_args.get("skills"):
        skills = normalize_str(cmds_args["skills"])
        embed.add_embed_field(name="Required skills", value=skills, inline=True)

    if cmds_args.get("discord") is not None:
        embed.add_embed_field(
            name="Discord", value=f'{cmds_args["discord"]}', inline=True
        )

    if cmds_args.get("bounty"):
        bounty = normalize_str(cmds_args["bounty"]).upper()
    else:
        bounty = "See the task details"
    embed.add_embed_field(name="Bounty", value=bounty, inline=True)

    if cmds_args.get("deadline"):
        deadline = cmds_args["deadline"]
    else:
        deadline = "Not specified"
    embed.add_embed_field(name="Due date", value=deadline, inline=True)

    is_in_progress = status and status.upper() == "IN PROGRESS"
    if is_in_progress and cmds_args.get("assignees"):
        assignees = normalize_str(cmds_args["assignees"]).lower()
        assignees_links = accounts_str_to_md_links(assignees)
        embed.add_embed_field(name="Assignees", value=assignees_links, inline=False)

    if cmds_args.get("note") is not None:
        embed.add_embed_field(name="Misc", value=f'{cmds_args["note"]}', inline=False)

    return embed


def listen_blockchain_ops(opNames: list):
    """Listens to Steem blockchain and yields specified operations.

    :param opNames: List of operations to yield
    :type opNames: list
    """
    bc = Blockchain(mode="head")
    block_num = bc.get_current_block_num()
    for op in bc.stream(opNames=opNames, start=block_num, threading=True):
        yield op


def listen_blockchain_comments():
    """Listens to blockchain for comments by specified accounts at
    Utopian task request posts and put them to a queue.

    """
    for comment_op in listen_blockchain_ops(["comment"]):
        if not comment_op["parent_author"] or comment_op["author"] not in ACCOUNTS:
            continue
        try:
            comment = Comment(f'@{comment_op["author"]}/{comment_op["permlink"]}')
        except beem.exceptions.ContentDoesNotExistsException:
            logger.info(
                "Comment does not exist. %s",
                f'@{comment_op["author"]}/{comment_op["permlink"]}',
            )
        except:
            logger.exception()
        else:
            root = comment.get_parent()
            logger.debug("%s, %s", comment["url"], root["url"])
            if is_utopian_task_request(root):
                logger.info(
                    "Added to comments queue - %s %s", comment["url"], root["url"]
                )
                QUEUE_COMMENTS.put_nowait((comment, root))


def background():
    t = Thread(target=listen_blockchain_comments)
    t.setDaemon(True)
    t.start()


def build_help_message():
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
        except:
            time.sleep(3)
            retry -= 1
        else:
            break


def send_help_message(comment: Comment, account: str, retry: int = 3):
    reply_message(comment, build_help_message(), account, retry)
    logger.info("Help message sent to %s", comment["url"])


def send_missing_status_message(comment: Comment, account: str, retry: int = 3):
    reply_message(comment, build_missing_status_message(), account, retry)
    logger.info("Missing status parameter message sent to %s", comment["url"])


def main():
    while True:
        try:
            queue_item = QUEUE_COMMENTS.get_nowait()
        except queue.Empty:
            continue

        comment: Comment = queue_item[0]
        cmd_str = comment["body"]
        logger.debug(cmd_str)
        parsed_cmd = parse_command(cmd_str)
        if parsed_cmd is None:
            logger.info("No command found")
            QUEUE_COMMENTS.task_done()
            continue
        elif parsed_cmd["help"] is not None and comment["author"] != ACCOUNT:
            replied = False
            for reply in comment.get_replies():
                if reply["author"] == ACCOUNT:
                    logger.info("Already replied with help command. %s", comment["url"])
                    replied = True
                    break
            if not replied:
                send_help_message(comment, ACCOUNT)
            QUEUE_COMMENTS.task_done()
            continue
        if parsed_cmd.get("status") is None:
            if len([x for x in parsed_cmd if parsed_cmd[x] is not None]) > 1:
                send_missing_status_message(comment, ACCOUNT)
            QUEUE_COMMENTS.task_done()
            continue
        root_comment = queue_item[1]
        category = get_category(root_comment, TASKS_PROPERTIES)
        if category is None:
            logger.info("No valid category found. %s", root_comment["url"])
            QUEUE_COMMENTS.task_done()
            continue
        category = TASKS_PROPERTIES[category]["category"]
        webhook = DiscordWebhook(
            url=DISCORD_WEBHOOK_TASKS,
            content=f'[{category.upper()}][{parsed_cmd["status"].upper()}] <{build_comment_link(root_comment)}>',
        )
        webhook.add_embed(build_discord_tr_embed(root_comment, parsed_cmd))
        webhook.execute()
        QUEUE_COMMENTS.task_done()


if __name__ == "__main__":
    setup_logger()
    logger.info("Utbot started")
    background()
    main()
