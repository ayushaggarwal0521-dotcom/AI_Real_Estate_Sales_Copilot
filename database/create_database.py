import sqlite3
import pandas as pd


CSV_PATH = "data/properties.csv"
DB_PATH = "database/properties.db"


def create_database():
    # Read the property data from CSV
    df = pd.read_csv(CSV_PATH)

    # Connect to SQLite database
    connection = sqlite3.connect(DB_PATH)

    # Store properties in SQLite
    df.to_sql(
        "properties",
        connection,
        if_exists="replace",
        index=False
    )

    connection.close()

    print(f"Database created successfully: {DB_PATH}")
    print(f"Total properties added: {len(df)}")


if __name__ == "__main__":
    create_database()