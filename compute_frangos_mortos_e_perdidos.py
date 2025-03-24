import psycopg2
from psycopg2 import sql
import pandas as pd
from datetime import datetime
from warnings import filterwarnings
filterwarnings("ignore", category=UserWarning, message='.*pandas only supports SQLAlchemy connectable.*')




def fetch_last_rows(date_to_see, row_limit=30*60):

    try:
        conn = psycopg2.connect(database="mytestdb",
            user="postgres",
            host='localhost',
            password="theia@24",
            port=5432)
        

        query = f"SELECT hora, chicken FROM paws WHERE data = '{date_to_see}' ORDER BY hora ASC"
        df_p = pd.read_sql_query(query, conn)
        query = f"SELECT hora, chicken FROM animals WHERE data = '{date_to_see}' ORDER BY hora ASC"
        df_a = pd.read_sql_query(query, conn)
        


        return df_a.tail(row_limit), df_p.tail(row_limit)

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    finally:
        #cur.close()
        conn.close()

date_to_see = datetime(year=2024, month=10, day=25)
df_a, df_p = fetch_last_rows(date_to_see)

#df_a = pd.read_csv("df_a2024-10-25.csv")
#df_p = pd.read_csv("df_p2024-10-25.csv")

#print(df_a['hora'].tail(30*60),df_a2['hora'])
#print(df_a['chicken'].tail(30*60),df_a2['chicken'])


import numpy as np

df = df_a#.tail(30*60)
df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S')
df['hora_in_seconds'] = (df['hora'] - df['hora'].iloc[0]).dt.total_seconds()

print('\n\n completed seconds conversion\n')
print(df['hora_in_seconds'])

# Ensure 'chicken' and 'hora_in_seconds' are in numeric format
df['chicken_derivative'] = np.gradient(df['chicken'], df['hora_in_seconds'])
print('\n\n completed derivative\n')
# Define the window size for moving average (e.g., 5)
window_size = 10
# Apply a moving average to smooth the 'chicken_derivative' column
df['chicken_derivative_smoothed'] = df['chicken_derivative'].rolling(window=window_size, center=True).mean()

print('\n\n completed filter\n')

reversed_derivative = df['chicken_derivative_smoothed'][::-1]


not_zero  = 0
for i, value in enumerate(reversed_derivative):
    if value != 0:
        not_zero += 1
        if not_zero > 100:
            break
    else: 
        not_zero = 0

print(f'indice nonzero = {i}')

# Step 2: Now search for the first interval of 100 consecutive zeros after encountering the first non-zero
if not_zero:
    # Initialize variables for finding the interval of 100 consecutive zeros
    zero_interval_start = None
    consecutive_zero_count = 0

    for j in range(i, len(reversed_derivative)):
        if reversed_derivative.iloc[j] == 0:
            if zero_interval_start is None:
                zero_interval_start = j
            consecutive_zero_count += 1
            
            if consecutive_zero_count == 100:
                # We've found the first interval of 100 consecutive zeros
                interval_indices = (zero_interval_start, j)
                break
        else:
            # Reset if we encounter a non-zero
            zero_interval_start = None
            consecutive_zero_count = 0
else:
    interval_indices = None


start = len(reversed_derivative)-interval_indices[1]
end = len(reversed_derivative)-interval_indices[0]

i_total = (start+end) // 2
print(i_total)

Frangos_in = df['chicken'].iloc[i_total]
Frangos_mortos = df['chicken'].iloc[-1]-df['chicken'].iloc[i_total]
Frangos_perdidos = df['chicken'].iloc[i_total] - df_p['chicken'].iloc[-1]

print(f'Frangos totais na entrada: {Frangos_in}')
print(f'Frangos que chegaram mortos: {Frangos_mortos}')
print(f'Frangos perdidos no processo: {Frangos_perdidos}')




if True:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('TkAgg') 
    plt.figure(figsize=(10, 6))
    plt.plot(df['hora_in_seconds'], (df['chicken']-df['chicken'].iloc[0])/(df['chicken'].iloc[-1]-df['chicken'].iloc[0]))
    plt.plot(df['hora_in_seconds'].iloc[start], (df['chicken'].iloc[start]-df['chicken'].iloc[0])/(df['chicken'].iloc[-1]-df['chicken'].iloc[0]), marker='o')
    plt.plot(df['hora_in_seconds'].iloc[end], (df['chicken'].iloc[end]-df['chicken'].iloc[0])/(df['chicken'].iloc[-1]-df['chicken'].iloc[0]), marker='o')
    plt.plot(df['hora_in_seconds'].iloc[i_total], (df['chicken'].iloc[i_total]-df['chicken'].iloc[0])/(df['chicken'].iloc[-1]-df['chicken'].iloc[0]), marker='o')
    plt.plot(df['hora_in_seconds'], df['chicken_derivative_smoothed']/df['chicken_derivative_smoothed'].max())
    plt.xlabel('Hora')
    plt.ylabel('Chicken')
    plt.title('Chicken Count Over Time')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


