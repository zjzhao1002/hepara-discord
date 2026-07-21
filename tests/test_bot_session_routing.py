import unittest
from types import MethodType
from types import SimpleNamespace

from hepara.bot import HeparaDiscordBot


class BotSessionRoutingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot_user = SimpleNamespace(id=99, display_name="HEPARA")
        self.bot = SimpleNamespace(user=self.bot_user, discord_reply_roots={})
        self.bot.get_discord_reply_root_message_id = MethodType(
            HeparaDiscordBot.get_discord_reply_root_message_id,
            self.bot,
        )
        self.bot.is_discord_bot_message = MethodType(
            HeparaDiscordBot.is_discord_bot_message,
            self.bot,
        )

    def make_message(
        self,
        *,
        message_id=123,
        channel_id=456,
        author_id=789,
        clean_content="@HEPARA hello",
        mentions=None,
        referenced_message=None,
    ):
        reference = None
        if referenced_message is not None:
            reference = SimpleNamespace(message_id=referenced_message.id)

        return SimpleNamespace(
            id=message_id,
            channel=SimpleNamespace(id=channel_id),
            author=SimpleNamespace(id=author_id, bot=False),
            clean_content=clean_content,
            mentions=mentions if mentions is not None else [self.bot_user],
            reference=reference,
            referenced_message=referenced_message,
        )

    async def test_mention_starts_new_conversation_from_message_id(self):
        message = self.make_message(message_id=111, channel_id=222)

        root_message_id = await HeparaDiscordBot.get_discord_root_message_id(self.bot, message)

        self.assertEqual(root_message_id, 111)
        self.assertEqual(
            HeparaDiscordBot.get_discord_session_id(self.bot, message, root_message_id),
            "discord-222-111",
        )
        self.assertEqual(
            HeparaDiscordBot.get_discord_user_id(self.bot, message, root_message_id),
            "discord-conversation-222-111",
        )

    async def test_reply_to_bot_continues_mapped_conversation(self):
        bot_reply = SimpleNamespace(id=333, author=self.bot_user, reference=None)
        message = self.make_message(
            message_id=444,
            channel_id=222,
            clean_content="continue",
            mentions=[],
            referenced_message=bot_reply,
        )
        self.bot.discord_reply_roots[333] = 111

        async def get_referenced_message(_message):
            return bot_reply

        self.bot.get_referenced_message = get_referenced_message

        root_message_id = await HeparaDiscordBot.get_discord_root_message_id(self.bot, message)

        self.assertEqual(root_message_id, 111)
        self.assertEqual(
            HeparaDiscordBot.get_discord_session_id(self.bot, message, root_message_id),
            "discord-222-111",
        )

    async def test_reply_to_bot_can_walk_references_to_original_mention(self):
        root_message = self.make_message(message_id=111, channel_id=222)
        first_bot_reply = SimpleNamespace(
            id=333,
            author=self.bot_user,
            mentions=[],
            reference=SimpleNamespace(message_id=111),
        )
        user_reply = SimpleNamespace(
            id=444,
            author=SimpleNamespace(id=123, bot=False),
            mentions=[],
            reference=SimpleNamespace(message_id=333),
        )
        second_bot_reply = SimpleNamespace(
            id=555,
            author=self.bot_user,
            mentions=[],
            reference=SimpleNamespace(message_id=444),
        )
        message = self.make_message(
            message_id=666,
            channel_id=222,
            clean_content="continue again",
            mentions=[],
            referenced_message=second_bot_reply,
        )
        messages_by_id = {
            111: root_message,
            333: first_bot_reply,
            444: user_reply,
            555: second_bot_reply,
        }

        async def get_referenced_message(current_message):
            return messages_by_id.get(current_message.reference.message_id)

        self.bot.get_referenced_message = get_referenced_message

        root_message_id = await HeparaDiscordBot.get_discord_root_message_id(self.bot, message)

        self.assertEqual(root_message_id, 111)

    async def test_non_mention_non_reply_does_not_start_conversation(self):
        message = self.make_message(clean_content="hello", mentions=[])

        async def get_referenced_message(_message):
            return None

        self.bot.get_referenced_message = get_referenced_message

        root_message_id = await HeparaDiscordBot.get_discord_root_message_id(self.bot, message)

        self.assertIsNone(root_message_id)

    def test_prompt_removes_bot_mention_when_present(self):
        message = self.make_message(clean_content="@HEPARA find papers")

        self.assertEqual(HeparaDiscordBot.get_discord_prompt(self.bot, message), "find papers")


if __name__ == "__main__":
    unittest.main()
