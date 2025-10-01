import pytest
import time
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from commands.payroll import payroll
from commands.reset import reset
from views.confirm_view import ConfirmView

@pytest.fixture(autouse=True)
def mock_get_db(mocker, test_database):
    """Fixture to automatically mock get_database in all relevant modules."""
    mocker.patch('utils.helpers.get_database', return_value=test_database)
    mocker.patch('commands.payroll.get_database', return_value=test_database, create=True)
    mocker.patch('commands.reset.get_database', return_value=test_database, create=True)

class TestPayrollCommand:
    @pytest.mark.asyncio
    async def test_payroll_confirm_false(self, mock_interaction, test_database):
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