# AllDebrid API plugin By Ryuk
# Made to be used standalone by Meliodas.
# Github: @TheDragonSinn

import json
import os
from io import BytesIO
from urllib.parse import quote_plus

from pyrogram.utils import parse_text_entities
from ub_core import BOT, Config, CustomDB, Message
from ub_core.utils import aio, bytes_to_mb
from ub_core.utils import post_to_telegraph as post_tgh

KEY = os.environ.get("DEBRID_TOKEN")
INDEX = os.environ.get("INDEX", "")
ALLOW_ALLDEBRID_LINKS = int(os.environ.get("ALLOW_ALLDEBRID_LINKS", 0))


async def init_task():
    Config.SUDO_CMD_LIST = [sudo_cmd["_id"] async for sudo_cmd in CustomDB("SUDO_CMD_LIST").find()]

    sudo = await CustomDB("COMMON_SETTINGS").find_one({"_id": "sudo_switch"}) or {}

    Config.SUDO = sudo.get("value", False)

    async for sudo_user in CustomDB("SUDO_USERS").find():
        config = Config.SUPERUSERS if sudo_user.get("super") else Config.SUDO_USERS
        config.append(sudo_user["_id"])

        if sudo_user.get("disabled"):
            Config.DISABLED_SUPERUSERS.append(sudo_user["_id"])


Config.INIT_TASKS.append(init_task())


@BOT.add_cmd("dhelp")
async def show_commands(bot: BOT, message: Message):
    await message.reply(
        """
CMD: U (Unrestrict magnets/links)
CMD: UT (Unrestrict Torrent)
CMD: T (Show Torrents)
CMD: DT (Delete Torrents)
    """
    )


# Get response from api and return json or the error
async def get_json(endpoint: str, query: dict, mode="get", **kwargs) -> dict | str:
    if not KEY:
        return "API key not found."

    api_url = os.path.join("https://api.alldebrid.com/v4", endpoint)
    params = {"agent": "bot", "apikey": KEY, **query}

    method = getattr(aio.session, mode)
    async with method(url=api_url, params=params, **kwargs) as ses:
        try:
            return await ses.json()
        except Exception as e:
            return str(e)


def get_request_params(query: str, flags: list) -> tuple[str, dict]:
    if query.startswith("http"):

        if "-save" not in flags:
            endpoint = "link/unlock"
            query = {"link": query}
        else:
            endpoint = "user/links/save"
            query = {"links[]": query}

    else:
        endpoint = "magnet/upload"
        query = {"magnets[]": query}

    return endpoint, query


async def fetch_torrents(message: Message) -> str | list[dict]:
    endpoint = "magnet/status"
    query = {}

    if "-l" not in message.flags and message.filtered_input:
        query = {"id": message.filtered_input}

    torrent_data = await get_json(endpoint=endpoint, query=query)

    if not isinstance(torrent_data, dict) or "error" in torrent_data:
        return str(torrent_data)

    torrent_list = torrent_data["data"]["magnets"]

    if not isinstance(torrent_list, list):
        torrent_list = [torrent_list]

    return torrent_list


def parse_debrid_links(data: dict) -> str:
    if not ALLOW_ALLDEBRID_LINKS:
        return ""

    links = data.get("links")

    if not links:
        return ""

    links = "\n".join(
        [f"<a href='{info.get('link', '')}'>{info.get('filename', '')}</a>" for info in links]
    )
    return f"<i>AllDebrid</i>: \n[ {links} ]"


def format_data(unrestricted_data: dict, sliced: bool = False) -> str:
    if not sliced:
        try:
            data = unrestricted_data["data"]["magnets"][0]
        except (IndexError, ValueError, KeyError):
            data = unrestricted_data["data"]
    else:
        data = unrestricted_data

    name = data.get("filename") or data.get("name", "")
    url = os.path.join(INDEX, quote_plus(name.strip("/"), safe="/?&=.-_~"))
    href_name = f"<a href='{url}'>{name}</a>"
    id = data.get("id")
    size = bytes_to_mb(data.get("size") or data.get("filesize", 0))
    ready = data.get("ready", "True")

    formatted_data = (
        f"Name: {href_name}"
        f"\nID: <code>{id}</code>"
        f"\nSize: <b>{size}mb</b>"
        f"\nReady: <i>{ready}</i>"
    )
    return formatted_data


# Unlock Links or magnets
@BOT.add_cmd("u")
async def unrestrict_magnets(bot: BOT, message: Message):
    """
    CMD: U (Unrestrict)
    INFO: Unrestrict one or more links/magnets
    FLAGS:
        -save: to save links
    USAGE: .u magnet | .u magnet1 magnet2 link
    """
    if not message.filtered_input:
        await message.reply("Give a magnet or link to unrestrict.")
        return

    for data in message.text_list[1:]:
        endpoint, query = get_request_params(data, message.flags)

        unrestricted_data = await get_json(endpoint=endpoint, query=query)

        if not isinstance(unrestricted_data, dict) or "error" in unrestricted_data:
            await message.reply(unrestricted_data)
            continue

        if "-save" in message.flags:
            await message.reply("Link Successfully Saved.")
            continue

        await message.reply(text=format_data(unrestricted_data), disable_preview=True)


# Get Status via id or Last torrents
@BOT.add_cmd("t")
async def get_torrent_info(bot: BOT, message: Message):
    """
    CMD: T (List Torrents)
    INFO: Get torrents information for.
    FLAGS:
        -l: to limit number of results, defaults to 1
    USAGE:  .t | .t -l 5
    """
    torrent_list = await fetch_torrents(message)

    if isinstance(torrent_list, str):
        await message.reply(torrent_list)
        return 

    ret_str = ""

    limit = int(message.filtered_input) if "-l" in message.flags else 1

    for data in torrent_list[0:limit]:
        status = data.get("status")
        name = data.get("filename")
        url = os.path.join(INDEX, quote_plus(name.strip("/"), safe="/?&=.-_~"))
        href_name = f"<a href='{url}'>{name}</a>"
        id = data.get("id")

        downloaded = ""
        if status == "Downloading":
            downloaded = f'<i>{bytes_to_mb(data.get("downloaded",0))}</i>/'

        size = f'{downloaded}<i>{bytes_to_mb(data.get("size",0))}</i> mb'

        ret_str += (
            f"\n\n<b>Name</b>: <i>{href_name}</i>"
            f"\nStatus: <i>{status}</i>"
            f"\nID: <code>{id}</code>"
            f"\nSize: {size}"
            f"\n{parse_debrid_links(data)}"
        )

    ret_str = f"<blockquote expandable=True>{ret_str.strip()}</blockquote>"

    text, _ = await parse_text_entities(bot, ret_str, None, [])

    if len(text) < 4096:
        await message.reply(ret_str, disable_preview=True)
    else:
        escaped_html = ret_str.replace("\n", "<br>")
        graph_url = await post_tgh(title="Magnets", text=escaped_html)
        await message.reply(text=graph_url, disable_preview=True)


@BOT.add_cmd("r")
async def restart_debrid(bot: BOT, message: Message):
    """
    CMD: R (Restart Expired Torrents)
    FLAGS:
        -l: to limit number of results to look for defaults to all.
    USAGE:
        .r (will check for expired torrents across all)
        .r -l 5 (look for expired in first 5 torrents)
        .r <id> (restart a specific torrent)
    """
    torrent_list: list[dict] = await fetch_torrents(message)

    if isinstance(torrent_list, str):
        await message.reply(torrent_list)
        return

    ret_str = ""

    for entry in torrent_list:
        if "expired" in entry.get("status", "").lower():
            json_data = await get_json(
                endpoint=endpoint, query={"id": int(entry.get("id"))}, method="post"
            )

            if isinstance(json_data, str):
                ret_str += f"\n\n{json_data}"
            else:
                ret_str += "\n\n" + json.dumps(json_data, indent=4, default=str)

    if ret_str:
        await message.reply(f"```\n{ret_str}```")
    else:
        await message.reply("No torrents to retry.", del_in=5)


# Delete a Magnet
@BOT.add_cmd("dt")
async def delete_torrent(bot: BOT, message: Message):
    """
    CMD: DT (Delete Torrent)
    INFO: Delete one or more torrents using IDs.
    USAGE: .dt id | .id id1 id2
    """
    endpoint = "magnet/delete"
    if not message.filtered_input:
        await message.reply("Enter an ID to delete")
        return

    for id in message.text_list[1:]:
        json = await get_json(endpoint=endpoint, query={"id": id})
        await message.reply(str(json))


@BOT.add_cmd("ut")
async def unrestrict_torrent_files(bot: BOT, message: Message):
    """
    CMD: UT (Unrestrict Torrent)
    INFO: Unrestrict Torrent files
    USAGE: .ut [reply to a torrent file]
    """
    try:
        assert message.replied.document.file_name.endswith(".torrent")
    except (AssertionError, AttributeError):
        await message.reply("Reply to a torrent file.")
        return

    # noinspection PyTypeChecker
    torrent_file: BytesIO = await message.replied.download(in_memory=True)
    torrent_file.seek(0)

    response_json = await get_json(
        endpoint="magnet/upload/file", query={}, mode="post", data={"files[]": torrent_file}
    )

    if not isinstance(response_json, dict) or "error" in response_json:
        await message.reply(response_json)
        return

    await message.reply(
        format_data(response_json["data"]["files"][0], sliced=True),
        disable_preview=True,
    )


if __name__ == "__main__":
    from ub_core import bot

    bot.run(bot.boot())
