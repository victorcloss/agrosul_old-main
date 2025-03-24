'''you can restrict the dcc.DatePickerSingle in Dash to show only certain available dates for selection. You can achieve this by using the min_date_allowed, max_date_allowed, and disabled_days properties of dcc.DatePickerSingle.

Here's how to configure it:

Example: Show Only Available Dates'''

import psycopg2
from datetime import timedelta, datetime, time
from psycopg2 import sql
import pytz
import pandas as pd


def update_today(time_zone='America/Sao_Paulo'):
    # Get the current time in the time_zone
    tz = pytz.timezone(time_zone)
    current_time = datetime.now(tz)
    today = current_time.strftime('%Y-%m-%d')

    print('\n\n Today is '+today+'\n\n')

    #today = '2024-09-06'
    yy = int(current_time.strftime('%Y'))
    mm = int(current_time.strftime('%m'))
    dd = int(current_time.strftime('%d'))
    return today, yy, mm, dd, current_time

# computes first day where there is info and the days where there is no info, used in the datepicker 
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
    cur = conn.cursor()

    # Query the database 
    columns = ['data', 'paw_a', 'paw_b', 'paw_c', 'hooks_empty']
    columns_str = ', '.join(columns)

    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = '''SELECT DISTINCT ON (data)  data, paw_a, paw_b, paw_c, hooks_empty 
            FROM paws 
            WHERE data >= %s 
            ORDER BY data, frame DESC'''
    
    # Execute the query with the parameterized last_data value
    cur.execute(query, (last_day,))

    # Fetch all results
    rows = cur.fetchall()
    
    # Optionally convert the result to a pandas DataFrame for easier manipulation
    df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
    
    query = '''SELECT DISTINCT ON (data)  data, chicken 
            FROM animals 
            WHERE data >= %s 
            ORDER BY data, frame DESC'''
    
    # Execute the query with the parameterized last_data value
    cur.execute(query, (last_day,))

    # Fetch all results
    rows = cur.fetchall()
    
    # Optionally convert the result to a pandas DataFrame for easier manipulation
    df_a = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
    
    df['chicken']=df_a['chicken']
    
    cur.close()
    conn.close()
    df['data'] = pd.to_datetime(df['data'])
    return df

def get_data_with_date(date_value):
    """ here we access the database and get df_p and df_a according to date_value"""    
    print(f'\n\nReading date from {date_value}')
    
    # Query the database 
    conn = psycopg2.connect(database="mytestdb",
                            user="postgres",
                            host='localhost',
                            password="theia@24",
                            port=5432)

    # Read only rows where 'data matches today's date
        # chicken comes from camera 1 tabel 'animals'
        # everything else from cam 2  table 'paws'
    columns = ['hora', 'chicken']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM animals WHERE data = '{date_value}'"
    df_a = pd.read_sql_query(query, conn)
    


    columns = ['hora', 'paw_a', 'paw_b', 'paw_c', 'hooks_empty']
    columns_str = ', '.join(columns)
    #Read only rows where 'data matches value_date's date and only the columns specified above
    query = f"SELECT {columns_str}  FROM paws WHERE data = '{date_value}'"
    df_p = pd.read_sql_query(query, conn)
    conn.close()

    df_a = df_a.rename(columns={"hora": "hora a"}, errors='raise')
    df_p = df_p.rename(columns={"hora": "hora p"}, errors='raise')

    return df_p.sort_values(by=['hora p']), df_a.sort_values(by=['hora a'])

def compute_chicken_before(df_a):
    tempo_in_out = time(0, 4, 40) # define o tempo que leva da camera de entrada até a camera de saida
    tempo_in_out_delta = timedelta(hours=tempo_in_out.hour, minutes=tempo_in_out.minute, seconds=tempo_in_out.second)

    # Convert the 'time' column to datetime.datetime to enable arithmetic
    df_a['time_as_datetime'] = df_a['hora a'].apply(lambda t: datetime.combine(datetime.today(), t))
    


    last_time = df_a['time_as_datetime'].iloc[-1]
    adjusted_time = last_time - tempo_in_out_delta



    # Find the nearest 'time' in the DataFrame
    nearest_idx = (df_a['time_as_datetime'] - adjusted_time).abs().idxmin()
    chicken_before = df_a['chicken'].iloc[nearest_idx]

    '''print('nearest Index:')   
    print('\n\n now: ')
    print(last_time, len(df_a))
    print(' ago: ')
    print(adjusted_time, nearest_idx)
    print('\n\n chicken: '+str(df_a['chicken'].iloc[-1]))
    print('chicken_before: '+str(chicken_before)+'\n\n')'''
    return chicken_before


def get_dia_data_display(df_p, df_a, data):
    #TD = update_today()
    if df_p.empty or df_a.empty:
        a = 0
        b = 0
        c = 0
        total = 0
        p_lost = 0
    else:
        total = df_a['chicken'].iloc[-1]
        a = df_p['paw_a'].iloc[-1]
        b = df_p['paw_b'].iloc[-1]
        c = df_p['paw_c'].iloc[-1]
        chicken_before = compute_chicken_before(df_a)
        p_lost = 2 * chicken_before - (a+b+c)
        if p_lost < 0:
            p_lost = 0
            
    return total, p_lost, a,b,c  

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


    df_past_days = get_past_days(18)


    TD, YY, MM, DD, CT = update_today()

    print(df_past_days)
    
    df_p, df_a = get_data_with_date(TD)
    get_dia_data_display(df_p, df_a, TD)
    df_a = compute_chicken_before(df_a)



