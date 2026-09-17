import sqlite3
from datetime import datetime

DB_PATH = "database/customers.db"


def get_or_create_customer(whatsapp_number, name=None):

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Check if customer already exists
    cursor.execute("""
        SELECT customer_id
        FROM customers
        WHERE whatsapp_number = ?
    """, (whatsapp_number,))

    customer = cursor.fetchone()

    current_time = datetime.now().isoformat()

    if customer:

        customer_id = customer[0]

        cursor.execute("""
            UPDATE customers
            SET last_contact_at = ?
            WHERE customer_id = ?
        """, (current_time, customer_id))

        connection.commit()
        connection.close()

        return customer_id

    # Create new customer
    cursor.execute("""
        INSERT INTO customers (
            whatsapp_number,
            name,
            first_contact_at,
            last_contact_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        whatsapp_number,
        name,
        current_time,
        current_time
    ))

    customer_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return customer_id