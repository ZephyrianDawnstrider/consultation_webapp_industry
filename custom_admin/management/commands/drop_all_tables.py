from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Drop all tables in the current database, handling foreign key constraints'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Disable all foreign key constraints
            cursor.execute("EXEC sp_msforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT all'")
            # Drop all tables
            cursor.execute("""
                DECLARE @sql NVARCHAR(MAX) = N'';
                SELECT @sql += 'DROP TABLE [' + SCHEMA_NAME(schema_id) + '].[' + name + '];'
                FROM sys.tables;
                EXEC sp_executesql @sql;
            """)
            # Enable all foreign key constraints
            cursor.execute("EXEC sp_msforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT all'")
        self.stdout.write(self.style.SUCCESS('All tables dropped successfully.'))
