import psycopg2
import pandas as pd
import sys

def table_create(table_name):
    """
    Creates a table in the PostgreSQL database with the given table name.
    """
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            database="mytestdb",
            user="postgres",
            host='localhost',
            password="theia@24",
            port=5432
        )
        cur = conn.cursor()

        # SQL command to create the table
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
	        "unidade_id" INTEGER,
            "date" DATE,
            "frangos_mortos" INTEGER,
            name VARCHAR(100),
            "chicken" INTEGER,
            "paw_a" INTEGER,
            "paw_b" INTEGER,
            "paw_c" INTEGER
        );
        """
        cur.execute(create_table_query)
        conn.commit()

        # Fetch and print the contents of the newly created table
        fetch_query = f'SELECT * FROM {table_name};'
        cur.execute(fetch_query)
        rows = cur.fetchall()
        columns = ['unidade_id', 'date', 'frangos_mortos', 'name', 'chicken', 'paw_a', 'paw_b', 'paw_c']
        df = pd.DataFrame(rows, columns=columns)
        print(f"Table '{table_name}' created successfully.")
        print("\nTable contents:")
        print(df)
        print("\nNumber of rows:", len(df))
        print("Number of columns:", len(df.columns))

    except Exception as e:
        print(f"Error creating table '{table_name}':", e)

    finally:
        cur.close()
        conn.close()

def table_delete(table_name):
    """
    Deletes the specified table from the PostgreSQL database.
    """
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            database="mytestdb",
            user="postgres",
            host='localhost',
            password="theia@24",
            port=5432
        )
        cur = conn.cursor()

        # SQL command to delete the table
        delete_table_query = f"DROP TABLE IF EXISTS {table_name};"
        cur.execute(delete_table_query)
        conn.commit()
        print(f"Table '{table_name}' deleted successfully.")

    except Exception as e:
        print(f"Error deleting table '{table_name}':", e)

    finally:
        cur.close()
        conn.close()

# Command line interface
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <create|delete> <table_name>")
        sys.exit(1)

    action = sys.argv[1].lower()
    table_name = sys.argv[2]

    if action == "create":
        table_create(table_name)
    elif action == "delete":
        table_delete(table_name)
    else:
        print("Invalid argument. Use 'create' to create the table or 'delete' to delete the table.")
