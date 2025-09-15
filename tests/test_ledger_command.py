"""
Tests for the ledger command.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from commands.ledger import ledger, LedgerView
from utils.helpers import get_database

class TestLedgerCommand:
    """Test the ledger command."""

    @pytest.mark.asyncio
    async def test_ledger_no_deposits(self, mock_interaction):
        """Test ledger command for a user with no deposits."""
        mock_interaction.created_at = datetime.now()
        mock_db = AsyncMock()
        mock_db.get_user_deposits_count.return_value = 0
        mock_db.get_user.return_value = {
            'user_id': '123',
            'username': 'TestUser',
            'total_melange': 0,
            'paid_melange': 0
        }

        with patch('commands.ledger.get_database', return_value=mock_db):
            # The decorator will provide command_start, and the test harness provides use_followup
            await ledger(mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        sent_embed = mock_interaction.followup.send.call_args[1]['embed']
        assert "You haven't made any melange yet!" in sent_embed.description

    @pytest.mark.asyncio
    async def test_ledger_with_deposits_sends_view(self, mock_interaction):
        """Test that the ledger command sends a view when there are deposits."""
        mock_interaction.created_at = datetime.now()
        mock_db = AsyncMock()
        mock_db.get_user_deposits_count.return_value = 15
        mock_db.get_user_deposits.return_value = [{'sand_amount': 100, 'created_at': datetime.now(), 'type': 'solo', 'melange_amount': 2.0}]
        mock_db.get_user.return_value = {
            'user_id': '123',
            'username': 'TestUser',
            'total_melange': 100,
            'paid_melange': 50
        }

        with patch('commands.ledger.get_database', return_value=mock_db):
            await ledger(mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        sent_view = mock_interaction.followup.send.call_args[1]['view']
        assert isinstance(sent_view, LedgerView)
        assert sent_view.total_pages == 2

    @pytest.mark.asyncio
    async def test_ledger_view_pagination(self, mock_interaction):
        """Test the pagination logic of the LedgerView."""
        mock_interaction.created_at = datetime.now()
        user = {
            'user_id': '123',
            'username': 'TestUser',
            'total_melange': 100,
            'paid_melange': 50
        }
        view = LedgerView(mock_interaction, user, 25) # 3 pages

        # Mock the database for the view
        mock_db = AsyncMock()
        mock_db.get_user_deposits.return_value = [{'sand_amount': 100, 'created_at': datetime.now(), 'type': 'solo', 'melange_amount': 2.0}]

        with patch('commands.ledger.get_database', return_value=mock_db):
            # Initial state
            assert view.current_page == 1

            # Simulate the initial interaction response
            mock_interaction.response.edit_message = AsyncMock()

            # Go to next page
            await view.next_button.callback(mock_interaction)
            assert view.current_page == 2
            mock_interaction.response.edit_message.assert_called_once()

            # Go to last page by manually setting page number
            view.current_page = 3
            await view.update_view(mock_interaction)
            assert view.next_button.disabled

            # Go to previous page
            await view.previous_button.callback(mock_interaction)
            assert view.current_page == 2
            assert not view.next_button.disabled
            assert not view.previous_button.disabled

    @pytest.mark.asyncio
    async def test_ledger_single_page_disables_buttons(self, mock_interaction):
        """Test that the ledger view buttons are disabled for a single page."""
        mock_interaction.created_at = datetime.now()
        mock_db = AsyncMock()
        mock_db.get_user_deposits_count.return_value = 5
        mock_db.get_user_deposits.return_value = [{'sand_amount': 100, 'created_at': datetime.now(), 'type': 'solo', 'melange_amount': 2.0}]
        mock_db.get_user.return_value = {
            'user_id': '123',
            'username': 'TestUser',
            'total_melange': 100,
            'paid_melange': 50
        }

        with patch('commands.ledger.get_database', return_value=mock_db):
            await ledger(mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        sent_view = mock_interaction.followup.send.call_args[1]['view']
        assert isinstance(sent_view, LedgerView)
        assert sent_view.total_pages == 1
        assert sent_view.previous_button.disabled
        assert sent_view.next_button.disabled

    @pytest.mark.asyncio
    async def test_ledger_view_timeout(self):
        """Test that the view buttons are disabled on timeout."""
        view = LedgerView(MagicMock(), {}, 1)
        await view.on_timeout()
        assert view.previous_button.disabled
        assert view.next_button.disabled
