import sqlite3

DB_PATH = "database/customers.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT
        customer_id,
        whatsapp_number,
        name,
        first_contact_at,
        last_contact_at,
        lead_status
    FROM customers
""")

customers = cursor.fetchall()

print("\nCUSTOMERS IN CRM")
print("==============================")

for customer in customers:
    print(customer)

connection.close()