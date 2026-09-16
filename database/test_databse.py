import sqlite3


DB_PATH = "database/properties.db"


connection = sqlite3.connect(DB_PATH)

cursor = connection.cursor()


# Count total properties
cursor.execute("SELECT COUNT(*) FROM properties")

total_properties = cursor.fetchone()[0]

print(f"Total properties: {total_properties}")


# Get first 5 properties
cursor.execute("""
    SELECT property_id, title, city, location, bhk, price
    FROM properties
    LIMIT 5
""")

properties = cursor.fetchall()


print("\nFirst 5 properties:")

for property in properties:
    print(property)


connection.close()