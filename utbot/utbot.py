import json
import logging
import os
import queue
import time
from datetime import datetime
from queue import Queue
from threading import Thread

import beem
import requests
from beem.blockchain import Blockchain
from beem.comment import Comment

from constants import (
    ACCOUNT,
    ACCOUNTS,
    CATEGORIES_PROPERTIES,
    DISCORD_WEBHOOK_CONTRIBUTIONS,
    DISCORD_WEBHOOK_TASKS,
    TASKS_PROPERTIES,
    UI_BASE_URL,
)
from discord_webhook import DiscordEmbed, DiscordWebhook
from utils import (
    accounts_str_to_md_links,
    build_comment_link,
    build_help_message,
    build_missing_status_message,
    build_steem_account_link,
    get_category,
    infinite_loop,
    is_utopian_task_request,
    normalize_str,
    parse_command,
    reply_message,
    setup_logger,
)

# Queue
QUEUE_COMMENTS = Queue(maxsize=0)

# Utopian Rocks
UR_BASE_URL = "https://utopian.rocks"
UR_BATCH_CONTRIBUTIONS_URL = "/".join([UR_BASE_URL, "api", "batch", "contributions"])
UR_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
queue_contributions = Queue(maxsize=0)
last_seen_time = datetime.strftime(datetime.utcnow(), UR_DATE_FORMAT)

# Logger
logger = logging.getLogger(__name__)

####################################
# CONTRIBUTIONS
####################################


def build_contribution_embed(contribution: dict):
    color = 0
    thumbnail_url = None
    category = contribution.get("category")
    if category:
        color = int(CATEGORIES_PROPERTIES[category]["color"][1:], 16)
        thumbnail_url = CATEGORIES_PROPERTIES[category]["image_url"]
    embed = DiscordEmbed(title=contribution.get("title"))
    embed.set_color(color=color)
    embed.set_thumbnail(url=thumbnail_url)
    author = contribution.get("author")
    if author:
        embed.set_author(
            name=author,
            url=build_steem_account_link(author),
            icon_url=f"https://steemitimages.com/u/{author}/avatar",
        )
    if category:
        category_text = category
    else:
        category_text = "Unknown"
    embed.add_embed_field(name="Category", value=category_text.upper(), inline=True)
    embed.add_embed_field(
        name="Reviewer", value=contribution.get("moderator", "Unknown"), inline=True
    )
    embed.add_embed_field(
        name="Score", value=str(contribution.get("score", "Unknown")), inline=True
    )
    staff_picked = "Yes" if contribution.get("staff_picked") is True else "No"
    embed.add_embed_field(name="Picked by staff", value=staff_picked, inline=True)
    embed.add_embed_field(
        name="Created at", value=contribution.get("created", "Unknown"), inline=True
    )
    embed.add_embed_field(
        name="Reviewed at",
        value=contribution.get("review_date", "Unknown"),
        inline=True,
    )
    logger.debug("%s", embed.__dict__)
    return embed


def process_reviewed_contributions():
    """Sends messages with Discord Webhook."""
    try:
        contr = queue_contributions.get_nowait()
        logger.debug("%s", contr)
    except queue.Empty:
        return

    logger.debug("%s", contr)
    body = f"<{contr['url']}>"
    embeds = [build_contribution_embed(contr)]
    send_message_to_discord(DISCORD_WEBHOOK_CONTRIBUTIONS, body, embeds)
    queue_contributions.task_done()


def fetch_to_vote_contributions(session, url: str, retry: int = 3):
    """Fetches reviewed contributions from utopian.rocks that will be voted.
    \
    :param session: Requests session
    :type session:
    :param url: utopian.rocks url for contributions
    :type url: str
    :param retry: Number of tries
    :type retry: int
    :return: Response from utopian.rocks
    :rtype:
    """
    while retry > 0:
        logger.info("Fetching contributions %s", url)
        resp = session.get(url)
        if resp.status_code != 200:
            retry -= 1
            time.sleep(10)
            continue
        logger.debug("%s", resp.json())
        return resp.json()
    return None


def filter_contributions(contributions: list) -> list:
    """Filters out already reviewed contributions and task requests.

    :param contributions: contributions from utopian.rocks
    :type contributions: list
    :return: list of filtered contributions
    :rtype: list
    """
    tasks = set(TASKS_PROPERTIES.keys())
    filtered = [
        c
        for c in contributions
        if c["review_date"] > last_seen_time and c["category"] not in tasks
    ]
    logger.debug("Contributions: %s", filtered)
    return filtered


def put_contributions_to_queue():
    """Puts new reviewed contributions to a queue for processing."""
    global last_seen_time
    with requests.Session() as session:
        contributions = fetch_to_vote_contributions(session, UR_BATCH_CONTRIBUTIONS_URL)
        logger.info("Fetched %d contributions from utopian.rocks", len(contributions))
        logger.debug(contributions)
        if not contributions:
            return
    if isinstance(contributions, str):
        contributions = json.loads(contributions)
    contributions = filter_contributions(contributions)
    logger.info("%d new contributions", len(contributions))
    for c in contributions:
        logger.debug("Adding to queue: %s", c)
        queue_contributions.put_nowait(c)
        if c["review_date"] > last_seen_time:
            last_seen_time = c["review_date"]


#############################################
# TASKS
#############################################


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
    description = None
    if cmds_args.get("description"):
        description = cmds_args["description"].strip()
    embed = DiscordEmbed(title=title, description=description)
    author = comment["author"]
    embed.set_author(
        name=author,
        url=f"{UI_BASE_URL}/@{author}",
        icon_url=f"https://steemitimages.com/u/{author}/avatar",
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


def listen_blockchain_ops(op_names: list):
    """Listens to Steem blockchain and yields specified operations.

    :param op_names: List of operations to yield
    :type op_names: list
    """
    bc = Blockchain(mode="head")
    block_num = bc.get_current_block_num()
    for op in bc.stream(opNames=op_names, start=block_num, threading=True):
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
            logger.exception("Error while fetching comment")
        else:
            root = comment.get_parent()
            logger.debug("%s, %s", comment["url"], root["url"])
            if is_utopian_task_request(root):
                logger.info(
                    "Added to comments queue - %s %s", comment["url"], root["url"]
                )
                QUEUE_COMMENTS.put_nowait((comment, root))


def process_cmd_comments():
    try:
        queue_item = QUEUE_COMMENTS.get_nowait()
    except queue.Empty:
        return

    comment: Comment = queue_item[0]
    cmd_str = comment["body"]
    logger.debug(cmd_str)
    parsed_cmd = parse_command(cmd_str)
    if parsed_cmd is None:
        logger.info("No command found in %s", comment["url"])
        QUEUE_COMMENTS.task_done()
        return
    elif parsed_cmd["help"] is not None and comment["author"] != ACCOUNT:
        replied = False
        for reply in comment.get_replies():
            if reply["author"] == ACCOUNT:
                logger.info("Already replied with help command to %s", comment["url"])
                replied = True
                break
        if not replied:
            send_help_message(comment, ACCOUNT)
        QUEUE_COMMENTS.task_done()
        return
    if parsed_cmd["help"] is None and parsed_cmd.get("status") is None:
        if len([x for x in parsed_cmd if parsed_cmd[x] is not None]) > 1:
            send_missing_status_message(comment, ACCOUNT)
        QUEUE_COMMENTS.task_done()
        return
    root_comment = queue_item[1]
    category = get_category(root_comment, TASKS_PROPERTIES)
    if category is None:
        logger.info("No valid category found. %s", root_comment["url"])
        QUEUE_COMMENTS.task_done()
        return
    content = f'[{parsed_cmd["status"].upper()}] <{build_comment_link(root_comment)}>'
    embeds = [build_discord_tr_embed(root_comment, parsed_cmd)]
    send_message_to_discord(DISCORD_WEBHOOK_TASKS, content, embeds)
    QUEUE_COMMENTS.task_done()


################################
# MISC
################################


def send_message_to_discord(webhook_url: str, content: str, embeds: list):
    webhook = DiscordWebhook(url=webhook_url, content=content)
    for embed in embeds:
        webhook.add_embed(embed)
    logger.debug(webhook.__dict__)
    webhook.execute()


def send_help_message(comment: Comment, account: str, retry: int = 3):
    reply_message(comment, build_help_message(), account, retry)
    logger.info("Help message sent to %s", comment["url"])


def send_missing_status_message(comment: Comment, account: str, retry: int = 3):
    reply_message(comment, build_missing_status_message(), account, retry)
    logger.info("Missing status parameter message sent to %s", comment["url"])


def background():
    if DISCORD_WEBHOOK_TASKS:
        Thread(target=listen_blockchain_comments, daemon=True).start()
        Thread(
            target=infinite_loop, args=(process_cmd_comments, 1), daemon=True
        ).start()
    if DISCORD_WEBHOOK_CONTRIBUTIONS:
        Thread(
            target=infinite_loop, args=(put_contributions_to_queue, 180), daemon=True
        ).start()
        Thread(
            target=infinite_loop, args=(process_reviewed_contributions, 2), daemon=True
        ).start()


if __name__ == "__main__":
    dirname = os.path.dirname(__file__)
    setup_logger(os.path.join(dirname, "logger_config.json"))
    logger.info("Utbot started")
    try:
        background()
        while True:
            continue
    except KeyboardInterrupt:
        logger.info("Stopping Utbot")
