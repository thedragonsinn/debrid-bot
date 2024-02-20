from app import BOT, bot
from app.core import Message


@bot.add_cmd(cmd="del")
async def delete_message(bot: BOT, message: Message) -> None:
    """
    CMD: DEL
    INFO: Delete the replied message.
    USAGE:
        .del
    """
    await message.delete(reply=True)


@bot.add_cmd(cmd="purge")
async def purge_(bot: BOT, message: Message) -> None | Message:
    start_message: int = message.reply_id
    if not start_message:
        return await message.reply("reply to a message")
    end_message: int = message.id
    messages: list[int] = [
        end_message,
        *[i for i in range(int(start_message), int(end_message))],
    ]
    await bot.delete_messages(
        chat_id=message.chat.id, message_ids=messages, revoke=True
    )
