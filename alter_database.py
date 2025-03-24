import psycopg2


alter_table_query = """
ALTER TABLE integrados
DROP COLUMN IF EXISTS contr_do_Dia;
"""


try:
    conn = psycopg2.connect(database = "mytestdb", 
                        user = "postgres", 
                        host= 'localhost',
                        password = "theia@24",
                        port = 5432)


    cursor = conn.cursor()


    # Execute the SQL command
    cursor.execute(alter_table_query)

    # Commit the changes to the database
    conn.commit()

    print("Operation performed succesfully.")

except Exception as error:
    print(f"Error: {error}")

finally:
    # Close the cursor and connection
    if cursor:
        cursor.close()
    if conn:
        conn.close()
    
    import sql_viewer
    


    