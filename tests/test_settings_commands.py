import pytest
from unittest.mock import patch, Mock, AsyncMock
from commands.settings import Settings
from utils.helpers import get_user_cut, get_guild_cut, get_region, update_user_cut, update_guild_cut, update_region

@pytest.fixture(autouse=True)
def mock_get_db(mocker, test_database):
    mocker.patch('commands.settings.get_database', return_value=test_database, create=True)

class TestSettingsCommand:
    @pytest.mark.asyncio
    async def test_settings_user_cut(self, mock_interaction):
        settings_command_group = Settings(bot=None)
        with patch('commands.settings.check_permission', return_value=True):
            update_user_cut(None)
            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.user_cut.callback(settings_command_group, mock_interaction, value=None)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "Not set" in embed.description
            mock_interaction.reset_mock()

            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.user_cut.callback(settings_command_group, mock_interaction, value=15)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **15%**" in embed.description
            assert get_user_cut() == 15
            mock_interaction.reset_mock()

            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.user_cut.callback(settings_command_group, mock_interaction, value=0)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **Unset**" in embed.description
            assert get_user_cut() is None

    @pytest.mark.asyncio
    async def test_settings_guild_cut(self, mock_interaction):
        settings_command_group = Settings(bot=None)
        with patch('commands.settings.check_permission', return_value=True):
            update_guild_cut(None)
            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.guild_cut.callback(settings_command_group, mock_interaction, value=None)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "is **10%**" in embed.description
            mock_interaction.reset_mock()

            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.guild_cut.callback(settings_command_group, mock_interaction, value=25)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **25%**" in embed.description
            assert get_guild_cut() == 25
            mock_interaction.reset_mock()

            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.guild_cut.callback(settings_command_group, mock_interaction, value=0)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **10%**" in embed.description
            assert get_guild_cut() == 10

    @pytest.mark.asyncio
    async def test_settings_region(self, mock_interaction):
        settings_command_group = Settings(bot=None)
        with patch('commands.settings.check_permission', return_value=True):
            update_region(None)
            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.region.callback(settings_command_group, mock_interaction, region=None)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "is **Not set**" in embed.description
            mock_interaction.reset_mock()

            mock_choice = Mock()
            mock_choice.name = "Europe"
            mock_choice.value = "eu"
            mock_interaction.response.is_done = Mock(return_value=True)
            await settings_command_group.region.callback(settings_command_group, mock_interaction, region=mock_choice)
            embed = mock_interaction.followup.send.call_args.kwargs['embed']
            assert "set to **Europe**" in embed.description
            assert get_region() == "eu"