import pytest
from unittest.mock import AsyncMock, MagicMock
from commands.payroll import payroll

@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock(id=123, display_name="Test Admin")
    interaction.created_at = MagicMock()
    return interaction

@pytest.fixture
def payroll_mocks(mocker):
    """Mocks dependencies for the payroll command."""
    mock_db = mocker.patch('commands.payroll.get_database', return_value=AsyncMock()).return_value
    mock_send_response = mocker.patch('commands.payroll.send_response', new_callable=AsyncMock)
    mocker.patch('commands.payroll.build_status_embed', return_value=MagicMock(build=lambda: "embed_obj"))
    mocker.patch('commands.payroll.logger')

    # This mock now correctly returns a tuple, as expected by the command
    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        result = await coro_func(*args, **kwargs)
        return result, 0.1
    mocker.patch('commands.payroll.timed_database_operation', side_effect=mock_timed_db_op)

    return mock_db, mock_send_response

@pytest.mark.asyncio
async def test_payroll_command_success(mock_interaction, payroll_mocks):
    # Given
    db_mock, send_response_mock = payroll_mocks
    db_mock.pay_all_pending_melange.return_value = {
        'total_paid': 300,
        'users_paid': 2
    }

    # When
    # The 'confirm' parameter does not exist, so it's removed.
    await payroll.__wrapped__(mock_interaction, command_start=0, use_followup=True)

    # Then
    db_mock.pay_all_pending_melange.assert_called_once_with(
        str(mock_interaction.user.id), mock_interaction.user.display_name
    )
    send_response_mock.assert_called_once_with(mock_interaction, embed="embed_obj", use_followup=True)

@pytest.mark.asyncio
async def test_payroll_command_no_pending_payments(mock_interaction, payroll_mocks):
    # Given
    db_mock, send_response_mock = payroll_mocks
    db_mock.pay_all_pending_melange.return_value = {
        'total_paid': 0,
        'users_paid': 0
    }

    # When
    await payroll.__wrapped__(mock_interaction, command_start=0, use_followup=True)

    # Then
    db_mock.pay_all_pending_melange.assert_called_once()
    send_response_mock.assert_called_once()
    # Ensure the correct embed is sent when no one is paid
    assert send_response_mock.call_args.kwargs['embed'] == "embed_obj"