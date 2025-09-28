import pytest
from unittest.mock import AsyncMock, MagicMock

# Import the function to be tested
from commands.sand import sand

@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = "12345"
    interaction.user.display_name = "Test User"
    return interaction

@pytest.fixture
def sand_mocks(mocker):
    """Mocks dependencies for the sand command."""
    mock_db_instance = AsyncMock()
    mocker.patch('commands.sand.get_database', return_value=mock_db_instance)
    mocker.patch('commands.sand.log_command_metrics')
    mocker.patch('commands.sand.logger')
    mocker.patch('commands.sand.build_status_embed', return_value=MagicMock(build=lambda: "embed_obj"))

    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        result = await coro_func(*args, **kwargs)
        return result, 0.1

    mocker.patch('commands.sand.timed_database_operation', side_effect=mock_timed_db_op)

    # Mock helper functions
    mocker.patch('utils.helpers.get_sand_per_melange_with_bonus', AsyncMock(return_value=50))
    mocker.patch('commands.sand.convert_sand_to_melange', AsyncMock(return_value=(20, 0))) # melange, remaining_sand
    mocker.patch('commands.sand.validate_user_exists', AsyncMock(return_value={'total_melange': 100}))

    # Mock send_response as it's used for sending all messages
    mock_send_response = mocker.patch('commands.sand.send_response', new_callable=AsyncMock)

    return mock_db_instance, mock_send_response

@pytest.mark.asyncio
async def test_sand_command_success(mock_interaction, sand_mocks):
    # Given
    db_mocks, send_response_mock = sand_mocks
    amount = 1000

    # When
    # Test the undecorated function to bypass decorator logic
    await sand.__wrapped__(mock_interaction, command_start=0, amount=amount, use_followup=True)

    # Then
    db_mocks.add_deposit.assert_called_once_with(
        mock_interaction.user.id,
        mock_interaction.user.display_name,
        amount,
        melange_amount=20,
        conversion_rate=50
    )
    db_mocks.update_user_melange.assert_called_once_with(mock_interaction.user.id, 20)
    send_response_mock.assert_called_once_with(mock_interaction, embed="embed_obj", use_followup=True)

@pytest.mark.asyncio
async def test_sand_command_invalid_amount(mock_interaction, sand_mocks):
    # Given
    db_mocks, send_response_mock = sand_mocks
    amount = 0

    # When
    await sand.__wrapped__(mock_interaction, command_start=0, amount=amount, use_followup=True)

    # Then
    db_mocks.add_deposit.assert_not_called()
    send_response_mock.assert_called_once()
    # Check the content of the call to send_response
    call_args = send_response_mock.call_args
    assert "must be between 1 and 10,000" in call_args.args[1]
    assert call_args.kwargs['ephemeral'] is True
    assert call_args.kwargs['use_followup'] is True