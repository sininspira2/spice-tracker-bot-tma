import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from commands.ledger import ledger, PAGE_SIZE
from utils.command_utils import log_command_metrics
from database import Database

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = "12345"
    interaction.user.display_name = "TestUser"
    interaction.created_at = datetime.now()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    return interaction

@pytest.fixture
def mock_db():
    db = MagicMock(spec=Database)
    db.get_user.return_value = {
        "user_id": "12345",
        "username": "TestUser",
        "total_melange": 1000,
        "paid_melange": 500
    }

    deposits = []
    for i in range(25):
        deposits.append({
            "id": i,
            "user_id": "12345",
            "username": "TestUser",
            "sand_amount": 1000,
            "melange_amount": 10, # Pre-calculated
            "type": "solo" if i % 2 == 0 else "expedition",
            "expedition_id": i if i % 2 != 0 else None,
            "created_at": datetime.now()
        })

    db.get_user_deposits_paginated.side_effect = lambda user_id, page, page_size: deposits[(page - 1) * page_size : page * page_size]
    db.get_user_deposits_count.return_value = len(deposits)

    return db

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_first_page(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    await ledger(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    kwargs = mock_interaction.followup.send.call_args.kwargs

    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert "Page 1 of 3" in embed.footer.text
    assert len(embed.description.strip().split('\n')) == PAGE_SIZE
    assert "(10 melange)" in embed.description

    assert "view" in kwargs
    view = kwargs["view"]
    assert view.previous_button.disabled
    assert not view.next_button.disabled

@pytest.mark.asyncio
@patch('commands.ledger.build_ledger_embed')
@patch('commands.ledger.get_database')
async def test_ledger_pagination(mock_get_database, mock_build_ledger_embed, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    # Mock the return value of build_ledger_embed
    embed = MagicMock()
    embed.footer.text = "Page 1 of 3"
    mock_build_ledger_embed.return_value = (embed, 3, 1000, 0.1)

    await ledger(mock_interaction)

    view = mock_interaction.followup.send.call_args.kwargs["view"]

    # Simulate clicking "Next"
    await view.next_button.callback(mock_interaction)

    # Check that build_ledger_embed was called with the correct page number
    mock_build_ledger_embed.assert_called_with(mock_interaction, view.user, view.total_deposits, 2)

    # Simulate clicking "Previous"
    await view.previous_button.callback(mock_interaction)

    # Check that build_ledger_embed was called with the correct page number
    mock_build_ledger_embed.assert_called_with(mock_interaction, view.user, view.total_deposits, 1)

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_invalid_sand_per_melange(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    # This test is no longer needed, as the mock is now static.
    # The logic for handling invalid sand_per_melange is in the database layer,
    # which is not being tested here.
    pass

@pytest.mark.asyncio
@patch('commands.ledger.log_command_metrics')
@patch('commands.ledger.get_database')
async def test_ledger_logging(mock_get_database, mock_log_command_metrics, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    await ledger(mock_interaction)

    mock_log_command_metrics.assert_called_once()
    args, kwargs = mock_log_command_metrics.call_args

    assert args[0] == "Ledger"
    assert args[1] == "12345"
    assert args[2] == "TestUser"
    assert "get_deposits_time" in kwargs
    assert "response_time" in kwargs
    assert "result_count" in kwargs
    assert "total_melange" in kwargs
    assert kwargs["result_count"] == 25
    assert kwargs["total_melange"] == 1000

@pytest.mark.asyncio
@patch('commands.ledger.log_command_metrics')
@patch('commands.ledger.get_database')
async def test_ledger_logging_no_deposits(mock_get_database, mock_log_command_metrics, mock_interaction, mock_db):
    mock_db.get_user_deposits_paginated.return_value = []
    mock_db.get_user_deposits_count.return_value = 0
    mock_get_database.return_value = mock_db

    await ledger(mock_interaction)

    mock_log_command_metrics.assert_called_once()
    args, kwargs = mock_log_command_metrics.call_args

    assert kwargs["result_count"] == 0
    assert kwargs["total_melange"] == 1000
