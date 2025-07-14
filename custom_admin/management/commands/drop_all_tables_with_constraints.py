from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Drop all tables in the current database by first dropping foreign key constraints'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Drop all foreign key constraints
            cursor.execute("""
                DECLARE @sql NVARCHAR(MAX) = N'';

                SELECT @sql += 'ALTER TABLE [' + OBJECT_SCHEMA_NAME(parent_object_id) + '].[' + OBJECT_NAME(parent_object_id) + '] DROP CONSTRAINT [' + name + '];'
                FROM sys.foreign_keys;

                EXEC sp_executesql @sql;
            """)

            # Drop all tables
            cursor.execute("""
                DECLARE @sql NVARCHAR(MAX) = N'';
                SELECT @sql += 'DROP TABLE [' + SCHEMA_NAME(schema_id) + '].[' + name + '];'
                FROM sys.tables;
                EXEC sp_executesql @sql;
            """)
        self.stdout.write(self.style.SUCCESS('All foreign key constraints and tables dropped successfully.'))
