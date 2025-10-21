import pytest
from unittest.mock import AsyncMock, MagicMock
from commands.pay import pay


@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock(id=123, display_name="Test Admin")
    interaction.created_at = MagicMock()
    return interaction


@pytest.fixture
def pay_mocks(mocker):
    """Mocks dependencies for the pay command."""
    mock_db = mocker.patch(
        "commands.pay.get_database", return_value=AsyncMock()
    ).return_value
    mock_send_response = mocker.patch(
        "commands.pay.send_response", new_callable=AsyncMock
    )
    mock_build_embed = mocker.patch(
        "commands.pay.build_status_embed",
        return_value=MagicMock(build=lambda: "embed_obj"),
    )
    mocker.patch("commands.pay.log_command_metrics")

    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        # In a real scenario, the coro would return data. We'll have the test setup do that.
        result = await coro_func(*args, **kwargs)
        return result, 0.1

    mocker.patch("commands.pay.timed_database_operation", side_effect=mock_timed_db_op)

    return mock_db, mock_send_response, mock_build_embed


@pytest.mark.asyncio
async def test_pay_command_success_full_amount(mock_interaction, pay_mocks):
    # Given
    db_mock, send_response_mock, _ = pay_mocks
    target_user = MagicMock(id=456, display_name="Harvester")
    db_mock.get_user_pending_melange.return_value = {
        "pending_melange": 500,
        "total_melange": 1000,
        "paid_melange": 500,
    }
    db_mock.pay_user_melange.return_value = 500  # Amount paid

    # When
    await pay.__wrapped__(
        mock_interaction,
        command_start=0,
        user=target_user,
        amount=None,
        use_followup=True,
    )

    # Then
    db_mock.get_user_pending_melange.assert_called_once_with(str(target_user.id))
    db_mock.pay_user_melange.assert_called_once_with(
        str(target_user.id),
        target_user.display_name,
        500,
        str(mock_interaction.user.id),
        mock_interaction.user.display_name,
    )
    send_response_mock.assert_called_once_with(
        mock_interaction, embed="embed_obj", use_followup=True
    )


@pytest.mark.asyncio
async def test_pay_command_no_pending_melange(mock_interaction, pay_mocks):
    # Given
    db_mock, send_response_mock, build_embed_mock = pay_mocks
    target_user = MagicMock(id=456, display_name="Harvester")
    db_mock.get_user_pending_melange.return_value = {
        "pending_melange": 0,
        "total_melange": 500,
        "paid_melange": 500,
    }

    # When
    await pay.__wrapped__(
        mock_interaction,
        command_start=0,
        user=target_user,
        amount=None,
        use_followup=True,
    )

    # Then
    db_mock.get_user_pending_melange.assert_called_once_with(str(target_user.id))
    db_mock.pay_user_melange.assert_not_called()
    build_embed_mock.assert_called_once_with(
        title="💰 No Payment Due",
        description=f"**{target_user.display_name}** has no pending melange.",
        color=0x95A5A6,
        fields={"📊 Status": f"**Total:** 500 | **Paid:** 500 | **Pending:** 0"},
        timestamp=mock_interaction.created_at,
    )
    send_response_mock.assert_called_once_with(
        mock_interaction, embed="embed_obj", use_followup=True
    )


@pytest.mark.asyncio
async def test_pay_command_amount_exceeds_pending(mock_interaction, pay_mocks):
    # Given
    db_mock, send_response_mock, _ = pay_mocks
    target_user = MagicMock(id=456, display_name="Harvester")
    db_mock.get_user_pending_melange.return_value = {
        "pending_melange": 500,
        "total_melange": 1000,
        "paid_melange": 500,
    }

    # When
    await pay.__wrapped__(
        mock_interaction,
        command_start=0,
        user=target_user,
        amount=600,
        use_followup=True,
    )

    # Then
    db_mock.pay_user_melange.assert_not_called()
    send_response_mock.assert_called_once()
    assert "exceeds pending melange" in send_response_mock.call_args.args[1]
    assert send_response_mock.call_args.kwargs["ephemeral"] is True
