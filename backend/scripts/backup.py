"""Backup or restore the JARVIS SQLite database.

Usage (PowerShell, from C:\\JARVIS\\backend):
    .\\.venv\\Scripts\\python scripts\\backup.py create [label]
    .\\.venv\\Scripts\\python scripts\\backup.py list
    .\\.venv\\Scripts\\python scripts\\backup.py restore <backup-file-name>
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.services import backup


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "create"
    if action == "create":
        label = sys.argv[2] if len(sys.argv) > 2 else ""
        print(backup.create_backup(label))
    elif action == "list":
        for b in backup.list_backups():
            print(f"{b['name']}  {b['size']/1024:.0f} KB  {b['created']}")
    elif action == "restore":
        if len(sys.argv) < 3:
            print("restore needs the backup file name")
            return
        print(backup.restore_backup(sys.argv[2]))
    else:
        print("unknown action. use create | list | restore")


if __name__ == "__main__":
    main()
