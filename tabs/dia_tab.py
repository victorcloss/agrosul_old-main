
from dash import dcc, html, Dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from flask import Flask
import dash_player as dp
import plotly.graph_objs as go
import time
import pandas as pd
from datetime import datetime
import glob
import os

if __name__ == '__main__': 
    import tab_functions
else:    
    from tabs import tab_functions 
global TD, YY, MM, DD, CT 
TD, YY, MM, DD, CT = tab_functions.update_today()

dis_day_paws, st_day_paws, end_day_paws = tab_functions.get_date_picker_days('paws', 'chicken', 'data')


#Total, A, B, C = tab_functions.get_data_display(df_p, df_a)
paws_lost = 0
Total_in = 0
Total_out = 0
A = 0
B = 0
C = 0

def compute_display_data(df):
    # Convert 'hora' to datetime
    df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S')
    
    # Truncate 'hora' to only include the hour and minute (eliminate seconds)
    df['hora'] = df['hora'].dt.floor('min')  # 'min' stands for minute
    
    # Aggregate the data by minute and compute the mean 'chicken' values for each minute
    df_minute = df.groupby('hora', as_index=False)['chicken'].mean()

    # Create a complete range of minutes from the min to max 'hora'
    full_minute_range = pd.date_range(start=df_minute['hora'].min(), end=df_minute['hora'].max(), freq='min')

    # Reindex the dataframe to this new minute range
    df_full = df_minute.set_index('hora').reindex(full_minute_range)

    # Interpolate the missing 'chicken' values using linear interpolation
    df_full['chicken'] = df_full['chicken'].interpolate()

    # Reset index so that 'hora' becomes a column again
    df_full.reset_index(inplace=True)
    df_full.rename(columns={'index': 'hora'}, inplace=True)

    # Format 'hora' to display only the hour and minute
    df_full['hora'] = df_full['hora'].dt.strftime('%H:%M')

    # Final dataframe with missing times filled and 'chicken' values interpolated
    return df_full['hora'], df_full['chicken']



def delete_older_videos():
    # Path to your folder
    folder_path = '/var/www/html/stream/hls/'

    # Get all .pt files in the directory
    files = glob.glob(os.path.join(folder_path, '*.ts'))

    # Ensure there are .pt files in the directory
    if len(files)  > 3:
        # Sort files by modification time, the most recent files will be at the end
        files.sort(key=os.path.getmtime)

        # Keep the last three most recent files
        most_recent_files = files[-3:]

        # Delete all other .pt files
        for file in files[:-3]:
            os.remove(file)
            print(f"Deleted {file}")

        print(f"Most recent .pt files {most_recent_files} were not deleted.")
    else:
        print("Not enough .pt files to delete. Only three or fewer files in the directory.")


def define_line_trace(x, y, name = 'dados', color='royalblue', width=2):
    return go.Scatter(x=x, y=y, mode='lines', line=dict(color=color, width=width), name = name)


def define_total_frangos_layout(dtick):
    return go.Layout(title='Frangos',
                     xaxis={'title': 'Horário', 'tickangle': 0, 'dtick': dtick},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family),
                     )


def define_pie_trace(val, labe):
    return go.Pie(values=val, labels=labe,
                  textinfo='label+percent',
                  # textfont_size=20,
                  sort=False,
                  pull=[0, 0, 0.2],
                  marker=dict(colors=[tab_functions.colors['paw_a'], tab_functions.colors['paw_b'], tab_functions.colors['paw_c']])
                  )


def define_pie_layout():
    return go.Layout(title='Qualidade',
                     legend={'traceorder': 'normal'},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                     )




def define_bar_layout_dia():
    return go.Layout(barmode='group',
                     title={'text': 'Desempenho nos últimos dias'},
                     yaxis=dict(automargin=True, ticksuffix="  "),
                     xaxis={'tickangle': 0, 'tickfont': {'size': 14}},
                     font_family=tab_functions.font_family,
                     font={'size': 20},
                     hoverlabel=dict(
                         font_size=20,
                         font_family=tab_functions.font_family)
                     )

####################### layout defs [fim]


bar_layout_dia = define_bar_layout_dia()

# Dia Tab Layout
layout = dbc.Card([
        dcc.Interval(id='dia-atualiza dados', interval=60000, n_intervals=0),
        dbc.Row([
                dcc.DatePickerSingle(
                month_format='MMM YYYY',
                display_format='DD/MM/2024',    
                id='date-picker-dia',
                min_date_allowed=st_day_paws,
                max_date_allowed=TD,
                initial_visible_month=TD,  # To make sure the calendar starts on a month that has valid dates
                disabled_days=dis_day_paws,
                date=TD
        )
        ]),
        dbc.Row([
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Frangos Entrada', className='text-title'),
                html.H3(dbc.Badge(Total_in, color='primary', className="me-3", id='dia-badge-total'))]),
            ), xs=6, sm=6, md=2, lg=2
            ),
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Frangos Saída', className='text-title'),
                html.H3(dbc.Badge(Total_out, color='blue', className="me-3", id='dia-badge-patas'))]),
            ),xs=6, sm=6, md=2, lg=2
            ),
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Frangos Perdidos ', className='text-title'),
                html.H3(dbc.Badge(Total_in - Total_out, color='danger', className="me-3",
                                    id='dia-badge-perdidas'))]),
            ),xs=6, sm=6, md=2, lg=2
            ),
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Patas A \t  ', className='text-title'),
                html.H3(dbc.Badge(A, color='success', className="me-3", id='dia-badge-A'), )]),
            ),xs=6, sm=6, md=2, lg=2
            ),
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Patas B ' + '      ', className='text-title'),
                html.H3(dbc.Badge(B, color='warning', className="me-3", id='dia-badge-B'), )]),
            ),xs=6, sm=6, md=2, lg=2
            ),
            dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5('Patas C ', className='text-title'),
                html.H3(dbc.Badge(C, color='danger', className="me-3", id='dia-badge-C')),]
                , style={'justify-content': 'center'},),
            ),xs=6, sm=6, md=2, lg=2
            ),
        ], id='dia-dados'),

        dbc.Row([
            dbc.Col(dcc.Graph(id='dia-Frango Total', style={'display': 'none'}),
                xs=12, sm=12, md = 12, lg = 7, xl = 7),
            dbc.Col(dcc.Graph(id='dia-Pes-pie', style={'display': 'none'}),
                xs=12, sm=12, md = 12, lg = 5, xl = 5)
        ], id= 'plot-row'),
         # Add a reload button
        dbc.Row(
            dbc.Col(
                dbc.Button("Recarregar Vídeo", id="reload-button", color="primary", style = {'display': 'none'}),
                width=12
            )
        ),
        dbc.Row([
                dbc.Col(
                    dp.DashPlayer(
                                        id="player",
                                        url="https://stream.theiasistemas.com.br/hls/ds-test-2.m3u8",
                                        controls=False,
                                        playing=True,
                                        width="100%",
                                        height="520px",
                                        muted=True,
                                    ),
                            xs=12, sm=12, md = 12, lg = 6, xl = 6),
                dbc.Col(
                    dp.DashPlayer(
                                        id="player2",
                                        url="https://stream.theiasistemas.com.br/hls/ds-test.m3u8",
                                        playing=True,
                                        controls=False,
                                        width="100%",
                                        height="520px",
                                        muted=True,
                                    ),
                            xs=12, sm=12, md = 12, lg = 6, xl = 6),                
            ], id='video'), 
    ], body=True, outline=False) # fim da aba 'dia'


# Callback tab 'financeiro'
def register_callbacks(dash_app):
    @dash_app.callback(    
        Output('dia-badge-total', 'children'),
        Output('dia-badge-patas', 'children'),
        Output('dia-badge-perdidas', 'children'),
        Output('dia-badge-A', 'children'),
        Output('dia-badge-B', 'children'),
        Output('dia-badge-C', 'children'),
        Output("dia-Frango Total", "figure"),
        Output("dia-Pes-pie", "figure"),
        Output('dia-Frango Total', 'style'),
        Output('dia-Pes-pie', 'style'),
        Output('date-picker-dia', 'disabled_days'),
        Output('date-picker-dia', 'max_date_allowed'),
        Input("dia-atualiza dados", "n_intervals"),
        Input("date-picker-dia","date")
    )
    def dados_dia_inicial(n_intervals, date_value):
        skip = 100

        #delete_older_videos()

        dis_day_paws, st_day_paws, end_day_paws = tab_functions.get_date_picker_days('paws', 'chicken', 'data')
        
        df_p, df_a = tab_functions.get_data_with_date(date_value, skip)
        df_p = df_p.sort_values(by=['hora'])
        df_a = df_a.sort_values(by=['hora'])

        if df_a.empty:
            df_a.loc[0] = [datetime.today(), 0] 
            Total_in_before = 0
        else:     
            Total_in_before = tab_functions.compute_chicken_before(df_a)
            
            
            

        if df_p.empty:
            df_p.loc[0] = [datetime.today(), 0, 0 ,0 ,0] 
#            trace_total_paws = define_line_trace(pd.DataFrame([0]), pd.DataFrame([0]), 'Saída', 'firebrick')            
#            trace_ABC_pizza = define_pie_trace([0, 0, 0], tab_functions.labels)            
        


        aX, aY = compute_display_data(df_a)
        pX, pY = compute_display_data(df_p)

        #Xa_axis = df_a['hora'].iloc[::skip]
        #Xa_axis['time'] = pd.to_datetime(Xa_axis, format='%H:%M:%S').dt.time

        #Xp_axis = df_p['hora'].iloc[::skip] 
        #Xp_axis['time'] = pd.to_datetime(Xp_axis, format='%H:%M:%S').dt.time

#        trace_total_frangos = define_line_trace(Xa_axis, df_a['chicken'].iloc[::skip], 'Entrada')        
#        trace_total_paws = define_line_trace(Xp_axis, df_p['chicken'].iloc[::skip], 'Saída', 'firebrick')
        trace_total_frangos = define_line_trace(aX, aY, 'Entrada')        
        trace_total_paws = define_line_trace(pX, pY, 'Saída', 'firebrick')
        
        Total_in, Total_out, A, B, C = tab_functions.get_data_display(df_p.iloc[-1], df_a.iloc[-1])
        trace_ABC_pizza = define_pie_trace([A, B, C], tab_functions.labels)
            
            

        
        Frangos_perdidos = Total_in_before - Total_out if (Total_in_before - Total_out) > 0 else 0
        figure_Pes_pie = {'data': [trace_ABC_pizza], 'layout': define_pie_layout()}

        
        if len(aX) < 10000/skip:
            dtick = 15
        elif len(aX) < 20000/skip:
            dtick = 30
        else:
            dtick = 60
        
         # figura total    
        layout_total_frangos = define_total_frangos_layout(dtick)
        figure_total = {'data': [trace_total_frangos, trace_total_paws], 'layout': layout_total_frangos}




        return  [Total_in, 
                Total_out, 
                Frangos_perdidos, 
                A, B, C, 
                figure_total, figure_Pes_pie,
                {'margin-right': '5px', 'border': '0px black solid'},
                {'margin-right': '5px', 'border': '0px black solid'},
                dis_day_paws, end_day_paws,
                ]
    # Callback tab 'dados dia' [fim]

    @dash_app.callback(
        [Output('player', 'key'),
        Output('player2', 'key')],
        [Input('reload-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def reload_players(n_clicks):
        # Increment the key to force the players to reload
        return n_clicks, n_clicks


if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], 
                    url_base_pathname='/', 
                    server=app)
    dash_app.title = 'THEIA - dados diarios'
    dash_app.layout = layout
    register_callbacks(dash_app)  # Register the callback with the local app
    dash_app.run_server(debug=True)