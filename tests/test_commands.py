"""
Generic tests for bot commands using real database.
"""
import pytest
from unittest.mock import patch, Mock
from commands import COMMAND_METADATA
from commands.settings import Settings
from commands.split import split
from utils.helpers import get_user_cut, get_guild_cut, get_region, update_user_cut, update_guild_cut, update_region
import datetime
import inspect

def setup_split_mock_interaction(mock_interaction):
    """Helper function to set up the mock interaction for split command tests."""
    from unittest.mock import Mock, AsyncMock
    import discord

    mock_interaction.created_at = datetime.datetime.now(datetime.timezone.utc)
    async def mock_fetch_member(user_id):
        mock_user = Mock(spec=discord.Member)
        mock_user.id = int(user_id)
        mock_user.display_name = f"TestUser{user_id}"
        mock_user.mention = f"<@{user_id}>"
        return mock_user

    mock_interaction.guild.fetch_member = AsyncMock(side_effect=mock_fetch_member)
    mock_interaction.client.fetch_user = AsyncMock(side_effect=mock_fetch_member)
    mock_interaction.response.is_done.return_value = True
    return mock_interaction

class TestCommandResponsiveness:
    """Test that all commands respond appropriately with real database."""

    @pytest.mark.asyncio
    async def test_all_commands_respond(self, mock_interaction, test_database):
        """Test that all commands can execute and respond without crashing."""
        test_cases = [
            ('sand', 'sand', [100], {}),
            ('refinery', 'refinery', [], {}),
            ('leaderboard', 'leaderboard', [10], {}),
            ('help', 'help', [], {}),
            ('reset', 'reset', [True], {}),
            ('ledger', 'ledger', [], {}),
            ('expedition', 'expedition', [1], {}),
            ('pay', 'pay', [Mock(id=123, display_name="TestUser"), None], {}),
            ('payroll', 'payroll', [], {}),
        ]

        for module_name, function_name, args, kwargs in test_cases:
            try:
                command_module = __import__(f'commands.{module_name}', fromlist=[module_name])
                command_func = getattr(command_module, function_name)

                patch_target = f'commands.{module_name}.get_database'

                try:
                    with patch(patch_target, return_value=test_database):
                         await command_func(mock_interaction, *args, **kwargs)
                except AttributeError:
                    # If the command module does not have `get_database`, just call it.
                    await command_func(mock_interaction, *args, **kwargs)

                response_sent = (mock_interaction.followup.send.called or mock_interaction.response.send_message.called or mock_interaction.channel.send.called or mock_interaction.response.send_modal.called)
                assert response_sent, f"Command {function_name} did not send any response"
                mock_interaction.reset_mock()
            except Exception as e:
                pytest.fail(f"Command {function_name} failed with error: {e}")

    @pytest.mark.asyncio
    async def test_split_command_with_user_cut(self, mock_interaction, test_database):
        """Test the split command with the new user_cut parameter."""
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.get_database', return_value=test_database):
            await split(mock_interaction, 1000, "<@123> <@456>", guild=10, user_cut=20)
            assert mock_interaction.followup.send.called, "Split command with user_cut did not send a followup response"

    @pytest.mark.asyncio
    async def test_split_command_with_conflicting_user_cut(self, mock_interaction, test_database):
        """Test the split command with a conflicting user_cut and individual percentages."""
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.get_database', return_value=test_database):
            await split(mock_interaction, 1000, "<@123> 30", guild=10, user_cut=20)
            assert mock_interaction.followup.send.called
            kwargs = mock_interaction.followup.send.call_args.kwargs
            assert "You cannot provide individual percentages when using `user_cut`" in kwargs['content']

class TestSplitCommand:
    @pytest.mark.asyncio
    async def test_split_command_with_user_cut(self, mock_interaction, test_database):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.get_database', return_value=test_database):
            await split(mock_interaction, 1000, "<@123> <@456>", guild=10, user_cut=20)
            assert mock_interaction.followup.send.called
            kwargs = mock_interaction.followup.send.call_args.kwargs
            embed = kwargs['embed']
            assert '4 melange' in embed.fields[0].value

    @pytest.mark.asyncio
    async def test_split_command_with_invalid_user_cut(self, mock_interaction, test_database):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.get_database', return_value=test_database):
            await split(mock_interaction, 1000, "<@123> <@456>", guild=10, user_cut=110)
            assert mock_interaction.followup.send.called
            kwargs = mock_interaction.followup.send.call_args.kwargs
            assert "User cut percentage must be between 0 and 100" in kwargs['content']

    @pytest.mark.asyncio
    async def test_split_command_with_conflicting_user_cut(self, mock_interaction, test_database):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.get_database', return_value=test_database):
            await split(mock_interaction, 1000, "<@123> 30", guild=10, user_cut=20)
            assert mock_interaction.followup.send.called
            kwargs = mock_interaction.followup.send.call_args.kwargs
            assert "You cannot provide individual percentages when using `user_cut`" in kwargs['content']

    @pytest.mark.asyncio
    async def test_split_command_with_user_cut_and_guild_warning(self, mock_interaction, test_database):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        default_guild_cut = get_guild_cut()
        non_default_guild_cut = default_guild_cut + 10
        with patch('commands.split.get_database', return_value=test_database):
            await split(mock_interaction, 1000, "<@123> <@456>", guild=non_default_guild_cut, user_cut=20)
            assert mock_interaction.followup.send.called
            first_call_kwargs = mock_interaction.followup.send.call_args_list[0].kwargs
            total_percentage = 20 * 2
            expected_warning = f"User percentages ({total_percentage}%) and the specified guild cut ({non_default_guild_cut}%) do not sum to 100%"
            assert expected_warning in first_call_kwargs.get('content', '')

    @pytest.mark.asyncio
    async def test_split_command_uses_global_defaults(self, mock_interaction, test_database):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        update_guild_cut(20)
        update_user_cut(15)
        with patch('commands.split.get_database', return_value=test_database), \
             patch('commands.split.get_sand_per_melange_with_bonus', return_value=50.0):
            await split(mock_interaction, 1000, "<@123> <@456>", guild=None, user_cut=None)
            assert mock_interaction.followup.send.called
            kwargs = mock_interaction.followup.send.call_args.kwargs
            embed = kwargs['embed']
            assert '**TestUser123**: 3 melange (15.0%)' in embed.fields[0].value
            assert '**TestUser456**: 3 melange (15.0%)' in embed.fields[0].value
            assert '70.0%' in embed.fields[1].value
            assert '14 melange' in embed.fields[1].value
        update_guild_cut(None)
        update_user_cut(None)

class TestSettingsCommand:
    @pytest.mark.asyncio
    async def test_settings_user_cut(self, mock_interaction, test_database):
        settings_command_group = Settings(bot=None)
        with patch('commands.settings.check_permission', return_value=True), \
             patch('commands.settings.get_database', return_value=test_database):
            update_user_cut(None)
            await settings_command_group.user_cut.callback(settings_command_group, mock_interaction, value=None)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "Not set" in embed.description
            mock_interaction.reset_mock()

            await settings_command_group.user_cut.callback(settings_command_group, mock_interaction, value=15)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **15%**" in embed.description
            assert get_user_cut() == 15
            mock_interaction.reset_mock()

            await settings_command_group.user_cut.callback(settings_command_group, mock_interaction, value=0)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **Unset**" in embed.description
            assert get_user_cut() is None

    @pytest.mark.asyncio
    async def test_settings_guild_cut(self, mock_interaction, test_database):
        settings_command_group = Settings(bot=None)
        with patch('commands.settings.check_permission', return_value=True), \
             patch('commands.settings.get_database', return_value=test_database):
            update_guild_cut(None)
            await settings_command_group.guild_cut.callback(settings_command_group, mock_interaction, value=None)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "is **10%**" in embed.description
            mock_interaction.reset_mock()

            await settings_command_group.guild_cut.callback(settings_command_group, mock_interaction, value=25)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **25%**" in embed.description
            assert get_guild_cut() == 25
            mock_interaction.reset_mock()

            await settings_command_group.guild_cut.callback(settings_command_group, mock_interaction, value=0)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **10%**" in embed.description
            assert get_guild_cut() == 10

    @pytest.mark.asyncio
    async def test_settings_region(self, mock_interaction, test_database):
        settings_command_group = Settings(bot=None)
        with patch('commands.settings.check_permission', return_value=True), \
             patch('commands.settings.get_database', return_value=test_database):
            update_region(None)
            await settings_command_group.region.callback(settings_command_group, mock_interaction, region=None)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "is **Not set**" in embed.description
            mock_interaction.reset_mock()

            mock_choice = Mock()
            mock_choice.name = "Europe"
            mock_choice.value = "eu"
            await settings_command_group.region.callback(settings_command_group, mock_interaction, region=mock_choice)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **Europe**" in embed.description
            assert get_region() == "eu"

    def test_command_metadata_structure(self):
        """Test that all commands have proper metadata structure."""
        for command_name, metadata in COMMAND_METADATA.items():
            assert 'description' in metadata, f"Command {command_name} missing description"
            assert isinstance(metadata['description'], str), f"Command {command_name} description must be string"
            if 'aliases' in metadata:
                assert isinstance(metadata['aliases'], list), f"Command {command_name} aliases must be list"
            if 'params' in metadata:
                assert isinstance(metadata['params'], dict), f"Command {command_name} params must be dict"

    def test_command_functions_exist(self):
        """Test that all command functions can be imported and are callable."""
        function_name_map = {
            'sand': 'sand', 'refinery': 'refinery', 'leaderboard': 'leaderboard', 'split': 'split',
            'help': 'help', 'reset': 'reset', 'ledger': 'ledger', 'expedition': 'expedition',
            'pay': 'pay', 'payroll': 'payroll',
        }
        for command_name in COMMAND_METADATA.keys():
            try:
                command_module = __import__(f'commands.{command_name}', fromlist=[command_name])
                actual_function_name = function_name_map.get(command_name, command_name)
                command_func = getattr(command_module, actual_function_name, None)
                assert command_func is not None, f"Command function {actual_function_name} not found in {command_name}"
                assert callable(command_func), f"Command function {actual_function_name} is not callable"
            except ImportError as e:
                pytest.fail(f"Could not import command {command_name}: {e}")
            except AttributeError as e:
                pytest.fail(f"Command function {actual_function_name} not found in module {command_name}: {e}")