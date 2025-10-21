import pytest
from unittest.mock import AsyncMock, MagicMock

# Import the function to be tested
from commands.leaderboard import leaderboard


@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.guild = MagicMock()
    interaction.guild.name = "Test Guild"
    interaction.guild.icon.url = "http://test.com/icon.png"
    interaction.created_at = MagicMock()
    # Mock the async iterator for guild members
    interaction.guild.fetch_members.return_value = []
    return interaction


@pytest.fixture
def leaderboard_mocks(mocker):
    """Mocks dependencies for the leaderboard command."""
    mock_db_instance = AsyncMock()
    mocker.patch("commands.leaderboard.get_database", return_value=mock_db_instance)
    mocker.patch("commands.leaderboard.log_command_metrics")

    # Mock the response sender and the embed builders
    mock_send_response = mocker.patch(
        "commands.leaderboard.send_response", new_callable=AsyncMock
    )
    mock_build_leaderboard = mocker.patch(
        "commands.leaderboard.build_leaderboard_embed",
        return_value=MagicMock(build=lambda: "leaderboard_embed"),
    )
    mock_build_info = mocker.patch(
        "commands.leaderboard.build_info_embed",
        return_value=MagicMock(build=lambda: "info_embed"),
    )

    # Mock the timed db operation
    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        result = await coro_func(*args, **kwargs)
        return result, 0.1

    mocker.patch(
        "commands.leaderboard.timed_database_operation", side_effect=mock_timed_db_op
    )

    return mock_db_instance, mock_send_response, mock_build_leaderboard, mock_build_info


@pytest.mark.asyncio
async def test_leaderboard_command_success(mock_interaction, leaderboard_mocks):
    # Given
    db_mock, send_response_mock, build_leaderboard_mock, build_info_mock = (
        leaderboard_mocks
    )
    leaderboard_data = [
        {"user_id": "123", "total_melange": 1000},
        {"user_id": "456", "total_melange": 500},
    ]
    db_mock.get_leaderboard.return_value = leaderboard_data

    # When
    await leaderboard.__wrapped__(
        mock_interaction, command_start=0, limit=5, use_followup=True
    )

    # Then
    db_mock.get_leaderboard.assert_called_once_with(5)
    build_leaderboard_mock.assert_called_once()
    build_info_mock.assert_not_called()
    send_response_mock.assert_called_once_with(
        mock_interaction, embed="leaderboard_embed", use_followup=True
    )


@pytest.mark.asyncio
async def test_leaderboard_command_no_data(mock_interaction, leaderboard_mocks):
    # Given
    db_mock, send_response_mock, build_leaderboard_mock, build_info_mock = (
        leaderboard_mocks
    )
    db_mock.get_leaderboard.return_value = []

    # When
    await leaderboard.__wrapped__(
        mock_interaction, command_start=0, limit=5, use_followup=True
    )

    # Then
    db_mock.get_leaderboard.assert_called_once_with(5)
    build_leaderboard_mock.assert_not_called()
    build_info_mock.assert_called_once()
    send_response_mock.assert_called_once_with(
        mock_interaction, embed="info_embed", use_followup=True
    )


@pytest.mark.asyncio
async def test_leaderboard_invalid_limit(mock_interaction, leaderboard_mocks):
    # Given
    db_mock, send_response_mock, _, _ = leaderboard_mocks

    # When
    await leaderboard.__wrapped__(
        mock_interaction, command_start=0, limit=200, use_followup=True
    )

    # Then
    db_mock.get_leaderboard.assert_not_called()
    send_response_mock.assert_called_once()
    assert "Limit must be between 5 and 100" in send_response_mock.call_args.args[1]
    assert send_response_mock.call_args.kwargs["ephemeral"] is True
