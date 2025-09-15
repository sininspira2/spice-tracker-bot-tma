"""
Comprehensive database robustness tests using real database.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncpg
from database_orm import Database


class TestDatabaseColumnAccess:
    """Test that database operations use column names instead of positional indexing."""

    @pytest.mark.asyncio
    async def test_real_database_column_access(self, test_database):
        """Test that real database operations work correctly with column names."""
        user_id = "123456789"
        username = "TestUser"

        # Test user operations
        await test_database.upsert_user(user_id, username)
        user = await test_database.get_user(user_id)

        # Verify the result structure matches expected column names
        assert user is not None
        assert 'user_id' in user
        assert 'username' in user
        assert 'total_melange' in user
        assert 'paid_melange' in user
        assert 'created_at' in user
        assert 'last_updated' in user

        # Verify column access was used (not positional)
        assert user['user_id'] == user_id
        assert user['username'] == username

        # Test deposit operations
        await test_database.add_deposit(user_id, username, 1000)
        deposits = await test_database.get_user_deposits(user_id)

        # Verify the result structure
        assert isinstance(deposits, list)
        assert len(deposits) == 1
        deposit = deposits[0]
        assert 'id' in deposit
        assert 'user_id' in deposit
        assert 'username' in deposit
        assert 'sand_amount' in deposit
        assert 'type' in deposit
        assert 'expedition_id' in deposit
        assert 'created_at' in deposit

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection with realistic row data."""
        conn = AsyncMock()

        # Mock user row with all expected columns
        user_row = Mock()
        user_row.__getitem__ = Mock(side_effect=lambda key: {
            'user_id': '123456789',
            'username': 'TestUser',
            'total_melange': 100,
            'paid_melange': 50,
            'created_at': '2024-01-01T00:00:00Z',
            'last_updated': '2024-01-01T00:00:00Z'
        }.get(key, None))

        # Mock deposit row
        deposit_row = Mock()
        deposit_row.__getitem__ = Mock(side_effect=lambda key: {
            'id': 1,
            'user_id': '123456789',
            'username': 'TestUser',
            'sand_amount': 1000,
            'type': 'solo',
            'expedition_id': None,
            'created_at': '2024-01-01T00:00:00Z'
        }.get(key, None))

        conn.fetchrow.return_value = user_row
        conn.fetch.return_value = [deposit_row]

        return conn

    @pytest.mark.skip(reason="ORM uses SQLAlchemy sessions, not raw connections - test no longer applicable")
    @pytest.mark.asyncio
    async def test_get_user_uses_column_names(self, mock_connection):
        """Test that get_user method uses column names instead of positional indexing."""
        with patch.object(Database, '_get_session') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            db = Database("sqlite+aiosqlite:///:memory:")
            result = await db.get_user("123456789")

            # Verify the result structure matches expected column names
            assert result is not None
            assert 'user_id' in result
            assert 'username' in result
            assert 'total_melange' in result
            assert 'paid_melange' in result
            assert 'created_at' in result
            assert 'last_updated' in result

            # Verify column access was used (not positional)
            assert result['user_id'] == '123456789'
            assert result['username'] == 'TestUser'

    @pytest.mark.skip(reason="ORM uses SQLAlchemy sessions, not raw connections - test no longer applicable")
    @pytest.mark.asyncio
    async def test_get_user_deposits_uses_column_names(self, mock_connection):
        """Test that get_user_deposits method uses column names."""
        with patch.object(Database, '_get_session') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            db = Database("sqlite+aiosqlite:///:memory:")
            result = await db.get_user_deposits("123456789")

            # Verify the result structure
            assert isinstance(result, list)
            if result:  # If deposits exist
                deposit = result[0]
                assert 'id' in deposit
                assert 'user_id' in deposit
                assert 'username' in deposit
                assert 'sand_amount' in deposit
                assert 'type' in deposit
                assert 'expedition_id' in deposit
                assert 'created_at' in deposit

    @pytest.mark.skip(reason="ORM uses SQLAlchemy sessions, not raw connections - test no longer applicable")
    @pytest.mark.asyncio
    async def test_database_handles_missing_columns_gracefully(self):
        """Test that database operations handle missing columns gracefully."""
        conn = AsyncMock()

        # Mock row with missing columns (simulating schema mismatch)
        incomplete_row = Mock()
        incomplete_row.__getitem__ = Mock(side_effect=lambda key: {
            'user_id': '123456789',
            'username': 'TestUser',
            # Missing other columns
        }.get(key, None))

        conn.fetchrow.return_value = incomplete_row

        with patch.object(Database, '_get_session') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = conn

            db = Database("sqlite+aiosqlite:///:memory:")

            # This should not raise "record index out of range" error
            # Instead, it should handle missing columns gracefully
            try:
                result = await db.get_user("123456789")
                # Should either return None or handle missing data gracefully
                assert result is None or isinstance(result, dict)
            except (IndexError, KeyError) as e:
                pytest.fail(f"Database operation raised {type(e).__name__}: {e}")

    @pytest.mark.asyncio
    async def test_database_handles_empty_results(self):
        """Test that database operations handle empty results gracefully."""
        # Mock SQLAlchemy session
        session = AsyncMock()

        # Mock the result object for get_user (no user found)
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        # Mock the result object for get_user_deposits (no deposits found)
        deposits_result_mock = Mock()
        deposits_result_mock.scalars.return_value.all.return_value = []

        with patch.object(Database, '_get_session') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = session

            db = Database("sqlite+aiosqlite:///:memory:")

            # Test get_user with no results
            result = await db.get_user("nonexistent")
            assert result is None

            # Update mock for deposits test
            session.execute = AsyncMock(return_value=deposits_result_mock)

            # Test get_user_deposits with no results
            deposits = await db.get_user_deposits("nonexistent")
            assert deposits == []

    @pytest.mark.skip(reason="ORM uses SQLAlchemy sessions, not raw connections - test no longer applicable")
    @pytest.mark.asyncio
    async def test_database_handles_connection_errors(self):
        """Test that database operations handle connection errors gracefully."""
        with patch.object(Database, '_get_session') as mock_get_conn:
            mock_get_conn.side_effect = asyncpg.ConnectionDoesNotExistError("Connection failed")

            db = Database("sqlite+aiosqlite:///:memory:")

            # Should raise the connection error, not a column access error
            with pytest.raises(asyncpg.ConnectionDoesNotExistError):
                await db.get_user("123456789")


class TestDatabaseSchemaCompatibility:
    """Test database operations against different schema versions."""

    @pytest.mark.asyncio
    async def test_user_schema_compatibility(self):
        """Test that user operations work with expected schema."""
        # Mock SQLAlchemy session
        session = AsyncMock()

        # Mock user object with expected attributes
        user_mock = Mock()
        user_mock.user_id = '123456789'
        user_mock.username = 'TestUser'
        user_mock.total_melange = 100
        user_mock.paid_melange = 50
        user_mock.created_at = '2024-01-01T00:00:00Z'
        user_mock.last_updated = '2024-01-01T00:00:00Z'

        # Mock the result object
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = user_mock
        session.execute = AsyncMock(return_value=result_mock)

        with patch.object(Database, '_get_session') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = session

            db = Database("sqlite+aiosqlite:///:memory:")
            result = await db.get_user("123456789")

            # Verify all expected columns are present
            expected_columns = ['user_id', 'username', 'total_melange', 'paid_melange', 'created_at', 'last_updated']
            for column in expected_columns:
                assert column in result, f"Missing expected column: {column}"

    @pytest.mark.asyncio
    async def test_deposits_schema_compatibility(self):
        """Test that deposits operations work with expected schema."""
        # Mock SQLAlchemy session
        session = AsyncMock()

        # Mock deposit object with expected attributes
        deposit_mock = Mock()
        deposit_mock.id = 1
        deposit_mock.user_id = '123456789'
        deposit_mock.username = 'TestUser'
        deposit_mock.sand_amount = 1000
        deposit_mock.type = 'solo'
        deposit_mock.expedition_id = None
        deposit_mock.created_at = '2024-01-01T00:00:00Z'

        # Mock the result object for deposits
        deposits_result_mock = Mock()
        deposits_result_mock.scalars.return_value.all.return_value = [deposit_mock]
        session.execute = AsyncMock(return_value=deposits_result_mock)

        with patch.object(Database, '_get_session') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = session

            db = Database("sqlite+aiosqlite:///:memory:")
            result = await db.get_user_deposits("123456789")

            # Verify all expected columns are present
            expected_columns = ['id', 'user_id', 'username', 'sand_amount', 'type', 'expedition_id', 'created_at']
            if result:
                for column in expected_columns:
                    assert column in result[0], f"Missing expected column: {column}"


class TestDatabaseErrorHandling:
    """Test database error handling and recovery."""

    @pytest.mark.skip(reason="ORM uses SQLAlchemy sessions, not raw connections - test no longer applicable")
    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self):
        """Test that database operations handle connection errors properly."""
        with patch.object(Database, '_get_session') as mock_get_conn:
            # Mock connection that raises an error
            mock_get_conn.side_effect = asyncpg.ConnectionDoesNotExistError("Connection failed")

            db = Database("sqlite+aiosqlite:///:memory:")

            # Should raise the connection error
            with pytest.raises(asyncpg.ConnectionDoesNotExistError):
                await db.get_user("123456789")

            # Verify connection was attempted
            assert mock_get_conn.call_count == 1

    @pytest.mark.skip(reason="ORM uses SQLAlchemy sessions, not raw connections - test no longer applicable")
    @pytest.mark.asyncio
    async def test_database_logging_on_errors(self):
        """Test that database errors are properly logged."""
        with patch.object(Database, '_get_session') as mock_get_conn:
            # Create a mock connection that raises an error during fetchrow
            mock_conn = AsyncMock()
            mock_conn.fetchrow.side_effect = Exception("Database error")

            # Create a proper async context manager
            class MockContextManager:
                def __init__(self, conn):
                    self.conn = conn

                async def __aenter__(self):
                    return self.conn

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            mock_get_conn.return_value = MockContextManager(mock_conn)

            with patch('database.logger.database_operation') as mock_logger:
                db = Database("sqlite+aiosqlite:///:memory:")

                with pytest.raises(Exception):
                    await db.get_user("123456789")

                # Verify error was logged
                mock_logger.assert_called()
                call_args = mock_logger.call_args
                assert call_args[1]['success'] is False
                assert 'error' in call_args[1]
