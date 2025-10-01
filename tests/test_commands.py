"""
Tests for bot commands.
"""
import pytest
import time
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from commands.settings import Settings
from commands.split import split
from utils.helpers import get_user_cut, get_guild_cut, get_region, update_user_cut, update_guild_cut, update_region
import datetime
import discord

@pytest.fixture(autouse=True)
def mock_get_db(mocker, test_database):
    """Fixture to automatically mock get_database in all command modules."""
    mocker.patch('utils.helpers.get_database', return_value=test_database)
    for module in ['payroll', 'reset', 'split', 'settings']:
        mocker.patch(f'commands.{module}.get_database', return_value=test_database, create=True)

def setup_split_mock_interaction(mock_interaction):
    """Helper function to set up the mock interaction for split command tests."""
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

class TestSplitCommand:
    @pytest.mark.asyncio
    async def test_split_command_with_user_cut(self, mock_interaction):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.send_response') as mock_send_response:
            await split(mock_interaction, total_sand=1000, users="<@123> <@456>", guild=10, user_cut=20)
            assert mock_send_response.call_count == 2
            final_call_kwargs = mock_send_response.call_args.kwargs
            embed = final_call_kwargs['embed']
            assert '4 melange' in embed.fields[0].value

    @pytest.mark.asyncio
    async def test_split_command_with_invalid_user_cut(self, mock_interaction):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.send_response') as mock_send_response:
            await split(mock_interaction, total_sand=1000, users="<@123> <@456>", guild=10, user_cut=110)
            mock_send_response.assert_called_once()
            content_arg = mock_send_response.call_args.args[1]
            assert "User cut percentage must be between 0 and 100" in content_arg

    @pytest.mark.asyncio
    async def test_split_command_with_conflicting_user_cut(self, mock_interaction):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        with patch('commands.split.send_response') as mock_send_response:
            await split(mock_interaction, total_sand=1000, users="<@123> 30", guild=10, user_cut=20)
            mock_send_response.assert_called_once()
            content_arg = mock_send_response.call_args.args[1]
            assert "You cannot provide individual percentages when using `user_cut`" in content_arg

    @pytest.mark.asyncio
    async def test_split_command_with_user_cut_and_guild_warning(self, mock_interaction):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        default_guild_cut = get_guild_cut()
        non_default_guild_cut = default_guild_cut + 10
        with patch('commands.split.send_response') as mock_send_response:
            await split(mock_interaction, total_sand=1000, users="<@123> <@456>", guild=non_default_guild_cut, user_cut=20)
            assert mock_send_response.called
            first_call_args = mock_send_response.call_args_list[0].args
            content_arg = first_call_args[1]
            total_percentage = 20 * 2
            expected_warning = f"User percentages ({total_percentage}%) and the specified guild cut ({non_default_guild_cut}%) do not sum to 100%"
            assert expected_warning in content_arg

    @pytest.mark.asyncio
    async def test_split_command_uses_global_defaults(self, mock_interaction):
        mock_interaction = setup_split_mock_interaction(mock_interaction)
        update_guild_cut(20)
        update_user_cut(15)
        with patch('commands.split.get_sand_per_melange_with_bonus', return_value=50.0), \
             patch('commands.split.send_response') as mock_send_response:
            await split(mock_interaction, total_sand=1000, users="<@123> <@456>", guild=None, user_cut=None)
            assert mock_send_response.call_count == 2
            final_call_kwargs = mock_send_response.call_args.kwargs
            embed = final_call_kwargs['embed']
            assert '**TestUser123**: 3 melange (15.0%)' in embed.fields[0].value
            assert '**TestUser456**: 3 melange (15.0%)' in embed.fields[0].value
            assert '70.0%' in embed.fields[1].value
            assert '14 melange' in embed.fields[1].value
        update_guild_cut(None)
        update_user_cut(None)

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

class TestPayrollCommand:
    @pytest.mark.asyncio
    async def test_payroll_confirm_false(self, mock_interaction, test_database):
        from commands.payroll import payroll
        with patch('commands.payroll.send_response', new_callable=AsyncMock) as mock_send, \
             patch.object(test_database, 'pay_all_pending_melange', new_callable=AsyncMock) as mock_pay_all:
            await payroll.__wrapped__(mock_interaction, time.time(), confirm=False, use_followup=True)
            mock_pay_all.assert_not_called()
            mock_send.assert_called_once()
            kwargs = mock_send.call_args.kwargs
            assert "Payroll Cancelled" in kwargs['embed'].title
            assert kwargs['ephemeral'] is True

    @pytest.mark.asyncio
    async def test_payroll_confirm_true(self, mock_interaction, test_database):
        from commands.payroll import payroll
        with patch('commands.payroll.send_response', new_callable=AsyncMock) as mock_send, \
             patch.object(test_database, 'pay_all_pending_melange', new_callable=AsyncMock) as mock_pay_all:
            mock_pay_all.return_value = {'users_paid': 2, 'total_paid': 500}
            async def timed_op_side_effect(name, coro, *args, **kwargs):
                res = await coro(*args, **kwargs)
                return res, 0.1
            with patch('commands.payroll.timed_database_operation', side_effect=timed_op_side_effect):
                await payroll.__wrapped__(mock_interaction, time.time(), confirm=True, use_followup=True)
            mock_pay_all.assert_called_once()
            mock_send.assert_called_once()
            kwargs = mock_send.call_args.kwargs
            assert "Guild Payroll Complete" in kwargs['embed'].title
            assert "500" in kwargs['embed'].fields[0].value

class TestResetCommand:
    @pytest.mark.asyncio
    async def test_reset_confirm_false(self, mock_interaction, test_database):
        from commands.reset import reset
        with patch('commands.reset.send_response', new_callable=AsyncMock) as mock_send, \
             patch.object(test_database, 'reset_all_stats', new_callable=AsyncMock) as mock_reset_stats:
            await reset.__wrapped__(mock_interaction, time.time(), confirm=False, use_followup=True)
            mock_reset_stats.assert_not_called()
            mock_send.assert_called_once()
            kwargs = mock_send.call_args.kwargs
            assert "Reset Cancelled" in kwargs['embed'].title
            assert kwargs['ephemeral'] is True

    @pytest.mark.asyncio
    async def test_reset_confirm_true_then_confirm(self, mock_interaction, test_database):
        from commands.reset import reset
        mock_interaction.edit_original_response = AsyncMock()
        with patch('commands.reset.send_response', new_callable=AsyncMock) as mock_send, \
             patch.object(test_database, 'reset_all_stats', new_callable=AsyncMock) as mock_reset_stats:
            mock_reset_stats.return_value = 10
            async def timed_op_side_effect(name, coro, *args, **kwargs):
                return await coro(*args, **kwargs), 0.1

            with patch('commands.reset.timed_database_operation', side_effect=timed_op_side_effect):
                command_task = asyncio.create_task(reset.__wrapped__(mock_interaction, time.time(), confirm=True, use_followup=True))
                await asyncio.sleep(0.01)

                mock_send.assert_called_once()
                view = mock_send.call_args.kwargs.get('view')
                assert view is not None

                await view.confirm.callback(mock_interaction)
                await command_task

            mock_reset_stats.assert_called_once()
            mock_interaction.edit_original_response.assert_called_once()
            embed = mock_interaction.edit_original_response.call_args.kwargs['embed']
            assert "Refinery Reset Complete" in embed.title

    @pytest.mark.asyncio
    async def test_reset_confirm_true_then_cancel(self, mock_interaction, test_database):
        from commands.reset import reset
        mock_interaction.edit_original_response = AsyncMock()
        with patch('commands.reset.send_response', new_callable=AsyncMock) as mock_send, \
             patch.object(test_database, 'reset_all_stats', new_callable=AsyncMock) as mock_reset_stats:

            command_task = asyncio.create_task(reset.__wrapped__(mock_interaction, time.time(), confirm=True, use_followup=True))
            await asyncio.sleep(0.01)

            mock_send.assert_called_once()
            view = mock_send.call_args.kwargs.get('view')
            assert view is not None

            await view.cancel.callback(mock_interaction)
            await command_task

            mock_reset_stats.assert_not_called()
            mock_interaction.edit_original_response.assert_called_once()
            embed = mock_interaction.edit_original_response.call_args.kwargs['embed']
            assert "Reset Cancelled" in embed.title