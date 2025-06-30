import os
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Remove log files older than 7 days from the logs directory.'

    def handle(self, *args, **kwargs):
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        if not os.path.exists(logs_dir):
            self.stdout.write(f"Logs directory does not exist: {logs_dir}")
            return

        now = datetime.now()
        cutoff_time = now - timedelta(days=7)

        for root, dirs, files in os.walk(logs_dir):
            for file in files:
                if not file.lower().endswith('.log'):
                    continue
                full_file_path = os.path.join(root, file)
                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(full_file_path))
                    if file_mtime < cutoff_time:
                        os.remove(full_file_path)
                        self.stdout.write(f"Deleted old log file: {full_file_path}")
                    else:
                        self.stdout.write(f"Log file {full_file_path} is not older than 7 days.")
                except Exception as e:
                    self.stderr.write(f"Error processing file {full_file_path}: {e}")

        self.stdout.write("Cleanup of old log files completed.")
