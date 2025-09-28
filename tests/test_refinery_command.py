import pytest
from unittest.mock import AsyncMock, MagicMock

# Import the function to be tested
from commands.refinery import refinery

@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = "12345"
    interaction.user.display_name = "Test User"
    interaction.created_at = MagicMock() # for timestamp fallback
    return interaction

@pytest.fixture
def refinery_mocks(mocker):
    """Mocks dependencies for the refinery command."""
    mocker.patch('commands.refinery.get_database')
    mocker.patch('commands.refinery.log_command_metrics')
    mocker.patch('commands.refinery.logger')
    mock_send_response = mocker.patch('commands.refinery.send_response', new_callable=AsyncMock)
    mocker.patch('commands.refinery.build_status_embed', return_value=MagicMock(build=lambda: "embed_obj"))
    mocker.patch('commands.refinery.build_info_embed', return_value=MagicMock(build=lambda: "embed_obj"))

    # Mock validate_user_exists as it's the source of user data
    mock_validate_user = mocker.patch('commands.refinery.validate_user_exists', new_callable=AsyncMock)

    return mock_validate_user, mock_send_response

@pytest.mark.asyncio
async def test_refinery_command_existing_user(mock_interaction, refinery_mocks):
    # Given
    validate_user_mock, send_response_mock = refinery_mocks

    # Use side_effect to ensure the await returns the dictionary directly
    async def side_effect(*args, **kwargs):
        return {
            'total_melange': 1234,
            'paid_melange': 1000,
            'last_updated': 1672531200 # Example timestamp
        }
    validate_user_mock.side_effect = side_effect

    # When
    await refinery.__wrapped__(mock_interaction, command_start=0, use_followup=True)

    # Then
    validate_user_mock.assert_called_once()
    # The response for an existing user should also be ephemeral.
    send_response_mock.assert_called_once_with(mock_interaction, embed="embed_obj", use_followup=True, ephemeral=True)

@pytest.mark.asyncio
async def test_refinery_command_new_user(mock_interaction, refinery_mocks):
    # Given
    validate_user_mock, send_response_mock = refinery_mocks

    async def side_effect(*args, **kwargs):
        return None # No user found
    validate_user_mock.side_effect = side_effect

    # When
    await refinery.__wrapped__(mock_interaction, command_start=0, use_followup=True)

    # Then
    validate_user_mock.assert_called_once()
    send_response_mock.assert_called_once()
    # Check that the embed for new users was sent
    assert send_response_mock.call_args.kwargs['embed'] == "embed_obj"
    assert send_response_mock.call_args.kwargs['ephemeral'] is True