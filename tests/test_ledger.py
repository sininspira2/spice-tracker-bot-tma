import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from commands.ledger import ledger, PAGE_SIZE
from database import Database

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = "12345"
    interaction.user.display_name = "TestUser"
    interaction.created_at = datetime.now()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
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
            "melange_amount": 10,
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

    assert "view" in kwargs
    view = kwargs["view"]
    assert view.previous_button.disabled
    assert not view.next_button.disabled

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_pagination(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    await ledger(mock_interaction)

    view = mock_interaction.followup.send.call_args.kwargs["view"]

    # Simulate clicking "Next"
    await view.next_button.callback(mock_interaction)

    # Check that the embed was updated to page 2
    kwargs = mock_interaction.response.edit_message.call_args.kwargs
    embed = kwargs["embed"]
    assert "Page 2 of 3" in embed.footer.text

    # Simulate clicking "Previous"
    await view.previous_button.callback(mock_interaction)

    # Check that the embed was updated back to page 1
    kwargs = mock_interaction.response.edit_message.call_args.kwargs
    embed = kwargs["embed"]
    assert "Page 1 of 3" in embed.footer.text

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_melange_display(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    await ledger(mock_interaction)

    kwargs = mock_interaction.followup.send.call_args.kwargs
    embed = kwargs["embed"]

    assert "(10 melange)" in embed.description
    assert "**1,000** total | **500** paid | **500** pending" in embed.fields[0].value
