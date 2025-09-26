# Database Migrations

This project uses Alembic for database migrations to manage schema changes safely and version-controlled.

## Environment Configuration

The migration system uses environment variables for database configuration:

- **`DATABASE_URL`**: The database connection string (e.g., `postgresql://user:pass@localhost/dbname`)
- **`.env`**: Loads environment variables from `.env` file

## Migration Commands

### Using Alembic directly:

```bash
# Activate virtual environment first
source env/bin/activate

# Apply all pending migrations
alembic upgrade head

# Create a new migration (after model changes)
alembic revision --autogenerate -m "Description of changes"

# Check current migration status
alembic current

# See all migration heads
alembic heads

# Rollback one migration
alembic downgrade -1

# Rollback to specific migration
alembic downgrade <revision_id>
```

### Using the helper script:

```bash
# Initialize database with migrations
python migrate.py init

# Apply all pending migrations
python migrate.py upgrade

# Create new migration
python migrate.py create "Add new feature"

# Check migration status
python migrate.py status

# Rollback one migration
python migrate.py downgrade
```

## Development Workflow

1. **Make model changes** in `app/models.py`
2. **Generate migration**: `alembic revision --autogenerate -m "Description"`
3. **Review the generated migration** in `alembic/versions/`
4. **Apply migration**: `alembic upgrade head`
5. **Commit migration files** to git

## Production Deployment

1. **Set environment variables**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@prod-server/dbname"
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

## Migration Files

- **`alembic.ini`**: Alembic configuration
- **`alembic/env.py`**: Migration environment setup
- **`alembic/versions/`**: Individual migration files
- **`migrate.py`**: Helper script for common operations

## Important Notes

- **Always review** auto-generated migrations before applying
- **Test migrations** on a copy of production data first
- **Backup database** before running migrations in production
- **Commit migration files** to version control
- **Never edit** applied migration files

## Troubleshooting

### Migration fails with "column contains null values"
- This happens when adding NOT NULL columns to existing tables
- Edit the migration to handle existing data:
  ```python
  # Add column as nullable first
  op.add_column('table', sa.Column('new_col', sa.String(), nullable=True))

  # Update existing rows
  op.execute("UPDATE table SET new_col = 'default_value' WHERE new_col IS NULL")

  # Make column NOT NULL
  op.alter_column('table', 'new_col', nullable=False)
  ```

### Database connection issues
- Check `DATABASE_URL` environment variable
- Ensure database server is running
- Verify connection credentials
