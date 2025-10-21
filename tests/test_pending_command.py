import pytest
from unittest.mock import AsyncMock, MagicMock
from commands.pending import pending


@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock(id=123, display_name="Test Admin")
    interaction.created_at = MagicMock()
    return interaction


@pytest.fixture
def pending_mocks(mocker):
    """Mocks dependencies for the pending command."""
    mock_db = mocker.patch(
        "commands.pending.get_database", return_value=AsyncMock()
    ).return_value
    mock_send_response = mocker.patch(
        "commands.pending.send_response", new_callable=AsyncMock
    )
    mock_build_embed = mocker.patch(
        "commands.pending.build_status_embed",
        return_value=MagicMock(build=lambda: "embed_obj"),
    )

    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        result = await coro_func(*args, **kwargs)
        return result, 0.1

    mocker.patch(
        "commands.pending.timed_database_operation", side_effect=mock_timed_db_op
    )

    return mock_db, mock_send_response, mock_build_embed


@pytest.mark.asyncio
async def test_pending_command_with_payments(mock_interaction, pending_mocks):
    # Given
    db_mock, send_response_mock, _ = pending_mocks
    db_mock.get_all_users_with_pending_melange.return_value = [
        {"username": "User One", "pending_melange": 100},
        {"username": "User Two", "pending_melange": 200},
    ]

    # When
    await pending.__wrapped__(mock_interaction, command_start=0, use_followup=True)

    # Then
    db_mock.get_all_users_with_pending_melange.assert_called_once()
    send_response_mock.assert_called_once_with(
        mock_interaction, embed="embed_obj", use_followup=True
    )


@pytest.mark.asyncio
async def test_pending_command_no_payments(mock_interaction, pending_mocks):
    # Given
    db_mock, send_response_mock, build_embed_mock = pending_mocks
    db_mock.get_all_users_with_pending_melange.return_value = []

    # When
    await pending.__wrapped__(mock_interaction, command_start=0, use_followup=True)

    # Then
    db_mock.get_all_users_with_pending_melange.assert_called_once()
    build_embed_mock.assert_called_once_with(
        title="📋 Pending Melange Payments",
        description="✅ **No pending payments!**\n\nAll harvesters have been paid up to date.",
        color=0x00FF00,
        timestamp=mock_interaction.created_at,
    )
    send_response_mock.assert_called_once_with(
        mock_interaction, embed="embed_obj", use_followup=True
    )
