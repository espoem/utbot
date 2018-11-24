from constants import CMD_RE, UI_BASE_URL, CATEGORIES_PROPERTIES, TASKS_PROPERTIES


def parse_command(cmd_str):
    found = CMD_RE.search(cmd_str)
    if not found:
        return None
    print(found.groupdict())
    return found.groupdict()


def build_comment_link(comment):
    return f'{UI_BASE_URL}{comment["url"]}'


def build_steem_account_link(username):
    return f"{UI_BASE_URL}/@{username}"


def is_utopian_contribution(comment):
    tags = comment["tags"]
    has_utopian_tag = "utopian-io" in tags
    has_utopian_category = not set(CATEGORIES_PROPERTIES.keys()).isdisjoint(set(tags))
    return has_utopian_tag and has_utopian_category


def is_utopian_task_request(comment):
    tags = comment["tags"]
    has_utopian_tag = "utopian-io" in tags
    has_utopian_category = not set(TASKS_PROPERTIES.keys()).isdisjoint(set(tags))
    return has_utopian_tag and has_utopian_category


def get_category(comment, categories):
    for tag in comment["tags"]:
        if tag in categories:
            return tag
    return None


def normalize_str(str_line):
    items = str_line.split(",")
    items = [a.strip() for a in items if a]
    return ", ".join(items)


def accounts_str_to_md_links(str_line):
    items = str_line.split(",")
    items = [
        f"[{name.strip(' @')}]({build_steem_account_link(name.strip(' @'))})"
        for name in items
        if name
    ]
    return ", ".join(items)
