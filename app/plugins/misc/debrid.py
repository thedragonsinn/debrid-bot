# AllDebrid API plugin By Ryuk

import os
from urllib.parse import quote

from app import BOT, Message, bot
from app.utils.aiohttp_tools import aio
from app.utils.helpers import bytes_to_mb
from app.utils.helpers import post_to_telegraph as post_tgh

KEY = os.environ.get("DEBRID_TOKEN")
INDEX = os.environ.get("INDEX", "")


# Get response from api and return json or the error
async def get_json(endpoint: str, query: dict) -> dict | str:
    if not KEY:
        return "API key not found."
    api_url = os.path.join("https://api.alldebrid.com/v4", endpoint)
    params = {"agent": "bot", "apikey": KEY, **query}
    async with aio.session.get(url=api_url, params=params) as ses:
        try:
            json = await ses.json()
            return json
        except Exception as e:
            return str(e)


# Unlock Links or magnets
@bot.add_cmd("unrestrict")
async def debrid(bot: BOT, message: Message):
    if not message.flt_input:
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
        await message.reply(
            text=format_data(unrestricted_data), disable_web_page_preview=True
        )


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


def format_data(unrestricted_data: dict) -> str:
    try:
        data = unrestricted_data["data"]["magnets"][0]
    except (IndexError, ValueError, KeyError):
        data = unrestricted_data["data"]

    name = data.get("filename") or data.get("name", "")
    url = os.path.join(INDEX, quote(name.strip("/")))
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


# Get Status via id or Last 5 torrents
@bot.add_cmd("torrents")
async def torrents(bot: BOT, message: Message):
    endpoint = "magnet/status"
    query = {}

    if "-l" not in message.flags and message.flt_input:
        query = {"id": message.flt_input}

    torrent_data = await get_json(endpoint=endpoint, query=query)

    if not isinstance(torrent_data, dict) or "error" in torrent_data:
        await message.reply(torrent_data)
        return

    torrent_list = torrent_data["data"]["magnets"]

    if not isinstance(torrent_list, list):
        torrent_list = [torrent_list]

    ret_str = ""
    limit = int(message.flt_input) if "-l" in message.flags else 1

    for data in torrent_list[0:limit]:
        status = data.get("status")
        name = data.get("filename")
        url = os.path.join(INDEX, quote(name.strip("/")))
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
    if len(ret_str) < 4000:
        await message.reply(ret_str, disable_web_page_preview=True)
    else:
        escaped_html = ret_str.replace("\n", "<br>")
        graph_url = await post_tgh(title="Magnets", text=escaped_html)
        await message.reply(text=graph_url, disable_web_page_preview=True)


def parse_debrid_links(data: dict) -> str:
    links = data.get("links")
    if not links:
        return ""
    links = "\n".join(
        [
            f"<a href='{info.get('link', '')}'>{info.get('filename', '')}</a>"
            for info in links
        ]
    )
    return f"<i>AllDebrid</i>: \n[ {links} ]"


# Delete a Magnet
@bot.add_cmd("del_t")
async def delete_torrent(bot: BOT, message: Message):
    endpoint = "magnet/delete"
    if not message.flt_input:
        await message.reply("Enter an ID to delete")
        return
    for id in message.text_list[1:]:
        json = await get_json(endpoint=endpoint, query={"id": id})
        await message.reply(str(json))
