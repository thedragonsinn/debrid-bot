from app import Config, CustomDB


async def init_task():
    Config.SUDO_CMD_LIST = [
        sudo_cmd["_id"] async for sudo_cmd in CustomDB("SUDO_CMD_LIST").find()
    ]
    sudo = await CustomDB("COMMON_SETTINGS").find_one({"_id": "sudo_switch"}) or {}
    Config.SUDO = sudo.get("value", False)
    async for sudo_user in CustomDB("SUDO_USERS").find():
        config = Config.SUPERUSERS if sudo_user.get("super") else Config.SUDO_USERS
        config.append(sudo_user["_id"])
        if sudo_user.get("disabled"):
            Config.DISABLED_SUPERUSERS.append(sudo_user["_id"])
