import sqlite3

DB_PATH = "database/customers.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
""")

tables = cursor.fetchall()

print("CRM TABLES:")

for table in tables:
    print("-", table[0])

connection.close()