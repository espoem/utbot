# Utbot

Utbot is a simple tool to watch and react to activity on Steem blockchain through special commands written in a comment/post. Its purpose is to gather information about Utopian.io Task Requests and send a message to Discord server in a standardized way.

> Note: The bot currently doesn't validate the parameters. The caller is responsible for calling it with a valid values.

## Install

Requirements:

- Python 3.6

Installation steps:

*Utbot is not distributed in PyPi at the moment but you can install it locally.*

```
python -m venv venv
. venv/bin/activate
(venv) python install -e .
```

You need to set keys to a Steem account and a Discord webhooks URLs. You can set them either in a `./utbot/config.json` file or as an environment variables. You can also use `.env` file to keep your environment variables.

```bash
UT_PK= bot private posting key
UT_ACCOUNT= bot steem account
UT_WH_TASKS= discor webhook url
UT_WH_CONTRS= discord webhook url
```

## Commands

This section takes the default prefix `!` and bot_name `utbot` to show some examples of the commands and parameters.

### Help

`!utbot help`

A bot will respond with a short message that will navigate you to bot's potential commands.

### Send a message to Discord

Utbot handles a few of different parameters format. The intention was to allow to use inline format and also accept a format where each parameter is written on a separate line.

```
!utbot --status open --bounty 10 SBD --description "Short description of the task" --skills "Python, Flask, Steem" --deadline 2018-01-01 --discord <@351997733646761985>
```

<hr/>

```
!utbot
status: open
bounty: 10 SBD
description: "Short description of the task"
skills: "Python, Flask, Steem"
deadline: 2018-01-01
discord: <@351997733646761985>
```

#### Parameters

| Name | Values | Note| Status |
|-|-|-|-|
|status | open \| in progress \| closed | a status of a task request | **required** |
|bounty| 00 NAME | e.g. 10 SBD <br/> a bounty may contain more currencies delimited by comma | optional |
| description | "text" | text must be enclosed in double quotes | optional |
| skills | "skill1, skill2, skill3" | a set of skills separated by comma; must be enclosed in double quotes | optional|
| discord | <@0000000000> \| username#0000 | a user ID or username with discriminator | optional |
| deadline | 2018-01-01 | a date in format YYYY-MM-DD | optional |
| assignees | "\@steemname1, \@steemname2" | Steem mentions of assigned people; valid only for a task that is in progress | optional |

*You can obtain the Discord user ID by submitting `\@usermention` in a channel they are in or you can right click on a user's avatar and copy the ID after enabling developers tools.*

## Discord Message Examples

![example1](https://i.imgsafe.org/ac/aca679c48a.png)