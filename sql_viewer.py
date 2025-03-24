
import psycopg2
from psycopg2 import sql
import pandas as pd
from datetime import date, datetime
from warnings import filterwarnings
filterwarnings("ignore", category=UserWarning, message='.*pandas only supports SQLAlchemy connectable.*')

conn = psycopg2.connect(database = "mytestdb", 
                        user = "postgres", 
                        host= 'localhost',
                        password = "theia@24",
                        port = 5432)


cursor = conn.cursor()

# Fetch all table names from the database
cursor.execute("""SELECT table_name FROM information_schema.tables
       WHERE table_schema = 'public'""")
tables = cursor.fetchall()




# Print all table names and create DataFrame for each table
for table in tables:
    table_name = table[0]

    # Create a DataFrame for the current table
#    df = pd.read_sql_query(f"SELECT * FROM {table_name};", conn)


#    print(f" - length= {str(len(df))}, \n - columns= {str(df.columns)}")

    # Print the DataFrame
    #print(df)

# Query to get the number of rows for the specified table
    row_count_query = sql.SQL(
        """
        SELECT COUNT(*)
        FROM {}
        """
    ).format(sql.Identifier(table_name))

    columns_count_query = sql.SQL(
        """
        SELECT COUNT(column_name) 
        FROM information_schema.columns
        WHERE table_name = {}
        """
    ).format(sql.Literal(table_name))


    table_columns_query = sql.SQL(
        """
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name = {}
        """
    ).format(sql.Literal(table_name))
    # Execute the query to name columns
    cursor.execute(table_columns_query)
    column_names = cursor.fetchall()

# Execute the query to count rows
    cursor.execute(row_count_query)
    row_count = cursor.fetchone()[0]




# Ececutre the query to count columns
    cursor.execute(columns_count_query)
    column_count = cursor.fetchone()[0]

# Print the results
    print(f"{table_name}:\t {column_count} columns \t {row_count} rows")
    print(f'{column_names}\n\n')


# Print some data
today = datetime.now().strftime('%Y-%m-%d')
query = f"SELECT DISTINCT date FROM Integrados"# WHERE data = '{today}'"
new_data = pd.read_sql_query(query, conn)
#print(new_data.iloc[0:20,:])


# print available dates
query = f"SELECT DISTINCT data FROM animals"# WHERE data = '{today}'"
new_data = pd.read_sql_query(query, conn)
#print(new_data)

# print specific date
date_to_see = datetime(year=2024, month=10, day=9)
query = f"SELECT * FROM paws WHERE data = '{date_to_see}'"
date_data = pd.read_sql_query(query, conn)

print(f"\n\nData sendo exibida {date_to_see}\n")
if not date_data.empty:
    C = date_data['paw_c'].iloc[-1]
    B = date_data['paw_b'].iloc[-1]
    A = date_data['paw_a'].iloc[-1]
    hora = date_data['hora'].iloc[-1]
    print(f'paw A = {A}')
    print(f'paw B = {B}')
    print(f'paw C = {C}')
    hora_ini = date_data['hora'].iloc[0]
    hora_fim = date_data['hora'].iloc[-1]
    print(f'\n \n tabela PAws data f{date_to_see}\n hora inicio = {hora_ini}, hora fim= {hora_fim}')
else:
    print(f'sem dados patas no dia {date_to_see}')



# Create a cursor object
cursor = conn.cursor()

# SQL to delete duplicate rows, keeping the one with the lowest primary key (or first occurrence)
delete_query = '''
DELETE FROM resumo_dia a
USING resumo_dia b
WHERE a.ctid < b.ctid
AND a.date = b.date;
'''

# Execute the query
cursor.execute(delete_query)
conn.commit()


query = "SELECT * FROM resumo_dia ORDER BY date ASC;"
date_data = pd.read_sql_query(query, conn)
if not date_data.empty:
    print(f'\n \n tabela resumo_dia: {date_data[-20:-1]}')
else:
    print(f'sem dados ')

dates_to_retrieve =  ['2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05', '2025-01-06', '2025-01-07']
for date in dates_to_retrieve:
    cursor.execute("SELECT * FROM resumo_dia WHERE date = %s", (date,))
    rows = cursor.fetchall()
    print(rows)


# Close the cursor and disconnect from the database
cursor.close()
conn.close()

############################################## delete rows:

def delete_rows_by_date(table_name, delete_date):
    # Connect to your PostgreSQL database
    conn = psycopg2.connect(database = "mytestdb", 
                        user = "postgres", 
                        host= 'localhost',
                        password = "theia@24",
                        port = 5432)
    
    try:
        # Create a cursor object
        cur = conn.cursor()

        # Define the SQL DELETE query dynamically with table_name        
        if table_name == 'integrados':
            delete_query = f"DELETE FROM {table_name} WHERE date = %s"
        else:
            delete_query = f"DELETE FROM {table_name} WHERE data = %s"        

        # Execute the query with the specific date
        cur.execute(delete_query, (delete_date,))

        # Commit the changes to the database
        conn.commit()

        print(f"Rows with data = {delete_date} have been deleted from {table_name}.")
    
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        conn.rollback()  # Rollback in case of error

    finally:
        # Close the cursor and connection
        cur.close()
        conn.close()

#delete_rows_by_date('paws', '2024-09-20')


############################################## add column
def add_column_to_table( table_name, column_name, column_type="INTEGER"):    
    try:
        print('\n\nconnecting...')
        conn = psycopg2.connect(database = "mytestdb", 
                        user = "postgres", 
                        host= 'localhost',
                        password = "theia@24",
                        port = 5432)
        cur = conn.cursor()
        print('connected')

         # Using psycopg2.sql module to format identifiers properly
        alter_table_query = sql.SQL("""
            ALTER TABLE {table}
            ADD COLUMN {column} {type}
        """).format(
            table=sql.Identifier(table_name),
            column=sql.Identifier(column_name),
            type=sql.SQL(column_type)
        )
        print('altering table...')


        # Execute the SQL statement
        cur.execute(alter_table_query)
        # Commit the changes
        print('\n\n commiting\n')
        conn.commit()
        return f"Column '{column_name}' added successfully to table '{table_name}' as type '{column_type}'."
    except Exception as e:
        # Rollback in case of any errors
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        # Close the cursor and connection
        cur.close()
        conn.close()

#print(add_column_to_table("integrados", "frangos_perdidos"))


def create_table_resumo_dia():
    try:
        # Establish the connection to the PostgreSQL database
        
        conn = psycopg2.connect(database = "mytestdb", 
                        user = "postgres", 
                        host= 'localhost',
                        password = "theia@24",
                        port = 5432)
        
        # Create a cursor object to interact with the database
        cursor = conn.cursor()
        
        # SQL command to create the 'resumo_dia' table
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS resumo_dia (
            date DATE NOT NULL,
            empresa_id INT NOT NULL,
            frangos_entrada INT,
            frangos_mortos INT,
            frangos_perdidos INT,
            patas_A INT,
            patas_B INT,
            patas_C INT
        );
        '''
        
        # Execute the query to create the table
        cursor.execute(create_table_query)
        
        # Commit the transaction
        conn.commit()
        
        print("Table 'resumo_dia' created successfully.")
        
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error while creating the table:", error)
    
    finally:
        # Close the cursor and the connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Call the function to create the table
#create_table_resumo_dia()


