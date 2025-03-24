'''you can restrict the dcc.DatePickerSingle in Dash to show only certain available dates for selection. You can achieve this by using the min_date_allowed, max_date_allowed, and disabled_days properties of dcc.DatePickerSingle.

Here's how to configure it:

Example: Show Only Available Dates'''

import psycopg2
from datetime import timedelta, datetime
from psycopg2 import sql
import pytz
import pandas as pd

def get_date_picker_days(table, column_zero, column_dates):
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)
    cursor = conn.cursor()
    query = sql.SQL("""
        SELECT DISTINCT {column_dates}
        FROM {table}
        GROUP BY {column_dates}
        HAVING SUM({column_zero}) != 0;
        """).format(
    column_dates=sql.Identifier(column_dates),
    column_zero=sql.Identifier(column_zero),
    table=sql.Identifier(table)
    )
    cursor.execute(query)
    tuples= cursor.fetchall()
    available_dates = []
    for i in range(len(tuples)):
        A = tuples[i]
        available_dates.append(A[0])
    start_date = min(available_dates) 
    end_date = max(available_dates)
    all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    disabled_dates = [d for d in all_dates if d not in available_dates]
    return disabled_dates, start_date, end_date


def get_past_days(n_days=10):
    tz = pytz.timezone('America/Sao_Paulo')
    # Get the current time in the time_zone
    current_time = datetime.now(tz)
    # Get today's date
    today_time = current_time
    # Generate a list of the past n_days days
    last_day =  (today_time - timedelta(days=n_days))
    #print(f'\n\n last day = {last_day.date}')
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)


    # Query the database 
    columns = ['data', 'paw_a', 'paw_b', 'paw_c', 'hooks_empty']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM paws WHERE data >= '{last_day}'"
    df_p = pd.read_sql_query(query, conn)

    # Query the database 
    columns = ['data', 'chicken']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM animals WHERE data >= '{last_day}'"
    
    df_a = pd.read_sql_query(query, conn)



    conn.close()

    # get the last value of each date
    df_a = df_a.groupby('data', as_index=False).tail(1)
    df_a = df_a.sort_values(['data'])   
    df_past_days = df_p.groupby('data', as_index=False).tail(1)
    df_past_days = df_past_days.sort_values(['data'])

 
    df_past_days['chicken'] = df_a['chicken'].values

    
    print(f'\n\n Today:')
    print(df_past_days.iloc[-1].T)

#    print('\n\n last values')
#    print(df_past_days)

    return df_past_days



if __name__ == "__main__":
    # Get the disabled days
    table_name = 'paws'
    zero_column= 'paw_b'
    date_column= 'data'
    disabled_days, st_day, end_day = get_date_picker_days(table_name, zero_column, date_column)
    print(f'\nas datas one a coluna {zero_column} não possui dados na tabela {table_name} são:')
    for i in range(len(disabled_days)):
        print(disabled_days[i])    
    print(f'\ndata de inicio: {st_day}\ndata de fim: {end_day}\n\n')


    df_past_days = get_past_days(10)





