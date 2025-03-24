import dash
from dash import dcc, html, Dash, State, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from flask import Flask
import base64
import pandas as pd
from io import BytesIO
import os


if __name__ == '__main__': 
    import tab_functions
else:    
    from tabs import tab_functions 

TD, YY, MM, DD, CT = tab_functions.update_today()




dis_day_integrados, st_day_integrados, end_day_integrados = tab_functions.get_date_picker_days('integrados', 'chicken', 'date')


# Upload Tab Layout: aba simples com um seletor de data e um espaço para upload. 
# Além disso tem um html.Div 'output-uresumo' e um html.Div 'output-upload' onde colocamos os resultados da seleção de data e do arquivo de upload
layout = dbc.Card([
            dbc.Card([
                dbc.Row(dbc.Label("Para visualizar a tabela resumo, selecione a data:")),
                dbc.Row([
                    dbc.Col([
                        dcc.DatePickerSingle(
                            id='resumo-check',
                            month_format='MMM YYYY',
                            display_format='DD/MM/2024',
                            min_date_allowed=st_day_integrados,
                            max_date_allowed=TD,
                            initial_visible_month=TD,
                            disabled_days=dis_day_integrados,
                            date=TD,
                        )], xs=12, sm=12, md=4, lg=4, xl=4),
                ]),
                dbc.Row(html.Div(id='output-resumo')),
                html.Hr(),
                dbc.Row(html.H5("Upload das planilhas em formato 'xlsb':")),
                html.Div([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Arraste e solte ou aperte  ',
                            html.A('AQUI', href='#'),
                            '  para selecionar seus arquivos.',
                        ]),
                        style={
                            'width': '100%',
                            'height': '160px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        # Allow multiple files to be uploaded
                        multiple=False),
                ]),
                dbc.Row(html.Div(id='output-upload')),
            ], body=True, outline=False),
        ], body=True, outline=False, id='capture-card-upload')# fim da aba 'upload'


# Callback tab 'financeiro'
def register_callbacks(dash_app):
    # recebe a data e devolve a analise em 'output-resumo'
    @dash_app.callback(
        Output('output-resumo', 'children'),
        Input('resumo-check', 'date'))
    def update_output_resumo(date_value):    
        # com a data cria o dataframe resumo
        df_resumo = tab_functions.get_resumo_dia(date_value)
        print(f'\n\nData frame Resumo na aba upload: \n{df_resumo}')

        #print('\n\ncriando tabela\n\n')
        if not df_resumo.empty:
                
                df_display = df_resumo.iloc[:, 3:-1].copy()
                print(f'\n\nData frame Display na aba upload: \n{df_display}')
                df_display.columns = ['Integrado', 'Frangos', 'Patas A', 'Patas B', 'Patas C']
                table = dash_table.DataTable(
                    data=df_display.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in df_display.columns],
                    page_size=len(df_display.index),  # Adjust the page size as needed
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '5px'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                        }
                    )
                return html.Div([
    #                    html.H5(' '),
    #                    html.H5(f'Resumo do dia {str(date_value)}:'),
                        table
                        ])
        
        return {}
    # Callback tab 'resumo' [fim]

    # recebe o arquivo de upload e mostra na html.Div 'output-upload'
    @dash_app.callback(        
        Output('output-upload', 'children'),
        Output('resumo-check', 'disabled_days'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
    )
    def save_uploaded_files(content, filename):
        dis_day_integrados, _, _ = tab_functions.get_date_picker_days('integrados', 'chicken', 'date')                                
        if content is not None:
            if filename.endswith(('.xlsb')):
                # Decode the file content
                data = content.split(',')[1]
                decoded = base64.b64decode(data)
                try:# abre o arquivo e pega o nome (data) para salvar
                    with BytesIO(decoded) as file:
                        # Use the 'pyxlsb' engine for '.xlsb' files, and default engine for '.xlsx' files
                        if filename.endswith('.xlsb'):
                            df = pd.read_excel(file, engine='pyxlsb')
                            print(f'\n\n {df}\n\n')
                            # extract the date from the corresponding cell
                            #data_crua = df['Data'].iloc[0]
                            data_datetime = pd.to_datetime(df['Data'].iloc[0], origin='1899-12-30', unit='D')
                            #print(f'data crua: {data_crua}  e data processada {data_datetime}')
                        
                        elif filename.endswith('.xlsx'):
                            df = pd.read_excel(file)  # .xlsx files work with the default engine
                        
                            # extract the date from the corresponding cell
                            cell_value = df['Data'].iloc[0]
                            # Parse the date assuming the format is 'dd/mm/yyyy'
                            data_datetime = pd.to_datetime(cell_value, format='%d/%m/%Y')
                    
                        
                    

                    if pd.isnull(data_datetime):
                        #print('\n\nNaT -> wrong file\n\n')
                        return html.Div([
                            html.H6(f'Arquivo .xlsb na formatação errada: a célula A0 deve conter a data.'),
                        ]), dis_day_integrados

                    
                    new_name = data_datetime.strftime("%Y-%m-%d")
                    print('\n\n'+new_name+'\n')

                    # Save the file in the Uploads folder
                    if filename.endswith('.xlsb'):
                        save_path = os.path.join('uploads', new_name + '.xlsb')
                    elif filename.endswith('.xlsx'):    
                        save_path = os.path.join('uploads', new_name + '.xlsx')
                    with open(save_path, 'wb') as file:
                        file.write(decoded)

                    print(f'arquivo salvo em \n{save_path}\n')
                    df_prev = tab_functions.get_previsao_carga(save_path)
                    # Create a DataTable to display the contents of the uploaded file
                    table = dash_table.DataTable(
                        data=df_prev.to_dict('records'),
                        export_format="csv",
                        columns=[{"name": col, "id": col} for col in df_prev.columns],
                        page_size=len(df_prev.index),  # Adjust the page size as needed
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '5px'},
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        }
                    )

                    # aqui criamos o resumo a partir dos dados
                    print('\n criando resumo:\n')
                    df_resumo, ok_dados, ok_file = tab_functions.create_resumo(new_name)
                    print(new_name)
                    print(df_resumo)
                    if not df_resumo.empty:

                        print('\n\n Adicionando tabela resumo')
                        tab_functions.insert_dataframe_to_integrados(df_resumo)
                        dis_day_integrados, _, _ = tab_functions.get_date_picker_days('integrados', 'chicken', 'date')
                        



                    return html.Div([
                        html.H6(f'Upload dos dados do abate do dia {str(new_name)} feito com sucesso:'),
                        table
                    ]), dis_day_integrados
                except Exception as e:
                    return html.Div([
                        html.H6(f'Erro ao salvar o arquivo: {str(e)}'),
                    ]), dis_day_integrados
            else:
                return html.Div('Por favor, carregue arquivos no formato .xlsb.'), dis_day_integrados
        dis_day_integrados, _, _ = tab_functions.get_date_picker_days('integrados', 'chicken', 'date')         
        return [], dis_day_integrados
    # Callback tab 'upload dados' [fim]




if __name__ == '__main__':   
    print('\n\nrunning locally\n\n')
    app = Flask(__name__)
    dash_app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assests/styles.css'], 
                    url_base_pathname='/', 
                    server=app)
    dash_app.title = 'THEIA - upload'
    dash_app.layout = layout
    register_callbacks(dash_app)  # Register the callback with the local app
    dash_app.run_server(debug=True)