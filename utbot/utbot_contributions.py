import json
import logging
import queue
import time
from datetime import datetime
from queue import Queue
from threading import Thread

import requests
from beem.account import Account

from constants import CATEGORIES_PROPERTIES, CONFIG, TASKS_PROPERTIES
from discord_webhook import DiscordEmbed, DiscordWebhook
from utils import build_steem_account_link, setup_logger

UR_BASE_URL = "https://utopian.rocks"
UR_BATCH_CONTRIBUTIONS_URL = "/".join([UR_BASE_URL, "api", "batch", "contributions"])

UR_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

queue_contributions = Queue(maxsize=0)
last_seen_time = datetime.strftime(datetime.utcnow(), UR_DATE_FORMAT)
authors = {}
WEBHOOK_URL = CONFIG["discord"]["webhooks"]["contributions"]

logger = logging.getLogger(__name__)


def fetch_to_vote_contributions(session, url: str, retry=3):
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


def filter_contributions(contributions):
    tasks = set(TASKS_PROPERTIES.keys())
    filtered = [
        c
        for c in contributions
        if c["review_date"] > last_seen_time
        # and c["category"] not in tasks
    ]
    logger.info("Contributions: %s", filtered)
    return filtered


def build_contribution_embed(contribution):
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
    author = authors.get(author)
    if not author:
        author = Account(contribution.get("author"))
    embed.set_author(
        name=author.name,
        url=build_steem_account_link(author.name),
        icon_url=f"https://steemitimages.com/u/{author.name}/avatar",
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


def put_contributions_to_queue():
    global last_seen_time
    with requests.Session() as session:
        contributions = fetch_to_vote_contributions(session, UR_BATCH_CONTRIBUTIONS_URL)
        logger.debug(contributions)
        if not contributions:
            return
    if isinstance(contributions, str):
        contributions = json.loads(contributions)
    contributions = filter_contributions(contributions)
    for c in contributions:
        logger.debug("Adding to queue: %s", c)
        queue_contributions.put_nowait(c)
        if c["review_date"] > last_seen_time:
            last_seen_time = c["review_date"]

        if c["author"] not in authors:
            authors[c["author"]] = Account(c["author"])


def infinite_loop(func, seconds, *args, **kwargs):
    while True:
        func(*args, **kwargs)
        time.sleep(seconds)


def send_message_to_discord(contribution, webhook_url):
    webhook = DiscordWebhook(
        url=webhook_url,
        content=f"[{contribution['category'].upper()}] <{contribution['url']}>",
    )
    webhook.add_embed(build_contribution_embed(contribution))
    logger.debug(webhook.__dict__)
    webhook.execute()


def background():
    t = Thread(target=infinite_loop, args=(put_contributions_to_queue, 180))
    t.setDaemon(True)
    t.start()


def main():
    global authors
    while True:
        authors = {}
        try:
            item = queue_contributions.get_nowait()
            logger.debug("%s", item)
        except queue.Empty:
            continue

        logger.debug("%s", item)
        send_message_to_discord(item, WEBHOOK_URL)
        queue_contributions.task_done()
        time.sleep(2)


if __name__ == "__main__":
    setup_logger()
    logger.info("Utbot contributions started")
    background()
    main()
