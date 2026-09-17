import sqlite3

DB_PATH = "database/customers.db"


def create_customer_database():

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # ============================================================
    # CUSTOMERS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (

            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,

            whatsapp_number TEXT UNIQUE NOT NULL,

            name TEXT,

            first_contact_at TEXT,

            last_contact_at TEXT,

            lead_status TEXT DEFAULT 'New'
        )
    """)

    # ============================================================
    # CUSTOMER REQUIREMENTS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_requirements (

            requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_id INTEGER UNIQUE NOT NULL,

            intent TEXT,

            city TEXT,

            location TEXT,

            bhk INTEGER,

            budget REAL,

            property_type TEXT,

            parking INTEGER,

            furnished TEXT,

            metro_preference INTEGER,

            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id)
        )
    """)

    # ============================================================
    # CUSTOMER INTERACTIONS
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_interactions (

            interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_id INTEGER NOT NULL,

            timestamp TEXT,

            message TEXT,

            message_type TEXT,

            FOREIGN KEY (customer_id)
                REFERENCES customers(customer_id)
        )
    """)

    connection.commit()
    connection.close()

    print("Customer CRM database created successfully.")
    print(f"Database: {DB_PATH}")
    print()
    print("Tables created:")
    print("1. customers")
    print("2. customer_requirements")
    print("3. customer_interactions")


if __name__ == "__main__":
    create_customer_database()