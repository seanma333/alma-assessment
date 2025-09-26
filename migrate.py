#!/usr/bin/env python3
"""
Database migration management script
"""
import subprocess
import sys
import os

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command>")
        print("Commands:")
        print("  init     - Initialize database with migrations")
        print("  upgrade  - Apply all pending migrations")
        print("  downgrade - Rollback one migration")
        print("  status   - Show migration status")
        print("  create   - Create a new migration")
        return

    command = sys.argv[1]

    # Activate virtual environment
    activate_venv = "source env/bin/activate && "

    if command == "init":
        print("Initializing database with migrations...")
        run_command(f"{activate_venv}alembic upgrade head")

    elif command == "upgrade":
        print("Applying migrations...")
        run_command(f"{activate_venv}alembic upgrade head")

    elif command == "downgrade":
        print("Rolling back one migration...")
        run_command(f"{activate_venv}alembic downgrade -1")

    elif command == "status":
        print("Migration status:")
        run_command(f"{activate_venv}alembic current")
        run_command(f"{activate_venv}alembic heads")

    elif command == "create":
        if len(sys.argv) < 3:
            print("Usage: python migrate.py create <message>")
            return
        message = sys.argv[2]
        print(f"Creating migration: {message}")
        run_command(f"{activate_venv}alembic revision --autogenerate -m '{message}'")

    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
