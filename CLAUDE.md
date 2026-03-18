# Spice Tracker Bot — Claude Code Guide

## Project Overview

A Python Discord bot for the game **Dune: Awakening** that manages guild-based spice sand → melange currency conversion, group expeditions, and guild treasury operations.

- **Discord framework**: discord.py 2.6.2+
- **Database**: SQLAlchemy async ORM — PostgreSQL (Supabase) in prod, SQLite for dev/tests
- **Migrations**: Alembic (`alembic/versions/`)
- **Deployment**: Fly.io via Docker
- **CI/CD**: GitHub Actions (lint, test, security, auto-deploy)

## Project Structure

```
bot.py              # Entry point — initializes bot, registers commands, health check
database_orm.py     # SQLAlchemy ORM models + Database class (all DB operations)
migrate.py          # Alembic migration manager
commands/           # One file per bot command; auto-discovered by commands/__init__.py
utils/              # Helpers: permissions, embeds, logging, pagination, decorators
views/              # Discord UI components (buttons, etc.)
alembic/            # Database migrations
tests/              # pytest test suite (25 files)
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in required values (see Environment Variables below)

# Run the bot
python bot.py

# Run database migrations
python migrate.py upgrade head
```

## Common Commands

| Task | Command |
|------|---------|
| Run bot | `python bot.py` |
| Run tests | `pytest tests/ -v --cov=. --cov-report=term-missing` |
| Run migrations | `python migrate.py upgrade head` |
| Format code | `black .` |
| Lint | `ruff check .` |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Bot token from Discord Developer Portal |
| `CLIENT_ID` | No | Discord application client ID |
| `DATABASE_URL` | Yes | PostgreSQL connection string (Supabase) |
| `ADMIN_ROLE_IDS` | No | Comma-separated Discord role IDs for admins |
| `ALLOWED_ROLE_IDS` | No | Comma-separated role IDs allowed to use the bot |
| `DEFAULT_HARVESTER_PERCENTAGE` | No | Harvester cut % for expeditions (default: 25.0) |
| `PORT` | No | Health check HTTP server port (default: 8080) |

## Key Patterns

### Adding a Command
Commands are auto-discovered from `commands/`. Create a new file following existing patterns:
- Use the `@command` decorator from `utils/base_command.py`
- Gate with `@is_admin` or `@is_officer` from `utils/decorators.py` as needed
- Use `EmbedBuilder` from `utils/embed_builder.py` for Discord responses
- Use the custom logger: `from utils.logger import get_logger; logger = get_logger(__name__)`

### Database Operations
All DB operations are async. Use the `Database` class from `database_orm.py`:
```python
async with db.get_session() as session:
    # your async ORM operations
```

### Permissions
Three permission levels enforced via decorators:
- `@is_admin` — admin role only
- `@is_officer` — admin or officer role
- No decorator — any allowed role

Permission checks live in `utils/permissions.py`.

### Data Model
- **Melange**: Always an integer (primary currency)
- **Sand**: Raw material; converted at a ratio (e.g., 50 sand = 1 melange, remainder stays as sand)
- **Guild cut**: Configurable percentage of each expedition that goes to the guild treasury

### Schema Changes
Always use Alembic migrations — never modify the DB schema directly:
```bash
alembic revision --autogenerate -m "description"
python migrate.py upgrade head
```

## Testing

- Minimum 80% test coverage required
- SQLite in-memory DB used for tests (fixtures in `tests/conftest.py`)
- All new features must include unit tests
- Run full suite before committing: `pytest tests/ -v --cov=. --cov-report=term-missing`

## Security

- Never hardcode tokens, passwords, or secrets — use environment variables
- All sensitive config is loaded via `python-dotenv` from `.env`
- Admin commands are permission-gated; validate all user inputs
