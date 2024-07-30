import os
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import logging

# Configuración del registro
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtener la ruta del directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'Basa de datos.xlsx')
logger.info(f"Ruta del archivo de datos: {file_path}")

# Verificar existencia del archivo
if os.path.exists(file_path):
    logger.info(f"El archivo {file_path} existe.")
else:
    logger.error(f"El archivo {file_path} no existe.")

# Cargar el archivo de Excel
try:
    data = pd.read_excel(file_path, sheet_name='Base de datos')
    niveles_avance = pd.read_excel(file_path, sheet_name='Niveles de Avance')
    logger.info("Archivos Excel cargados correctamente.")
except Exception as e:
    logger.error(f"Error al cargar el archivo Excel: {e}")
    raise

# Identificar los nombres de los productos y los niveles máximos para cada uno
productos = niveles_avance['Producto'].unique()
niveles_maximos = niveles_avance.groupby('Producto')['Nivel'].max().to_dict()

# Definir los colores y columnas basados en el análisis previo
colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6']
columns_num = ['Planificación', 'Informe diagnóstico', 'Perfil de egreso', 'Trayectoria de aprendizajes', 'Validación externa', 'Aprobación cuerpos colegiados']
columns_cat = ['Planificación1', 'Informe diagnóstico1', 'Perfil de egreso1', 'Trayectoria de aprendizajes1', 'Validación externa1', 'Aprobación cuerpos colegiados1']

# Agregar opción "Todas las carreras" al DataFrame
data_todas = pd.DataFrame([['Todas las carreras', 'Todas las carreras'] + [0] * (len(data.columns) - 2)], columns=data.columns)
data = pd.concat([data_todas, data], ignore_index=True)

# Inicializar la aplicación Dash
app = Dash(__name__)
server = app.server  # Añadir esta línea para que Gunicorn sepa dónde está el servidor
server.debug = True  # Forzar el modo debug en Flask

# Función para dividir texto en líneas más cortas
def wrap_labels(text, max_width=20):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) <= max_width:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())
    return "<br>".join(lines)

# Aplicar la función de división de texto a las descripciones
niveles_avance['Descripción nivel de avance'] = niveles_avance['Descripción nivel de avance'].apply(wrap_labels)

# Layout de la aplicación
app.layout = html.Div([
    html.H1("Avance del Rediseño Curricular por Carrera", style={'textAlign': 'center'}),
    dcc.Dropdown(
        id='facultad-dropdown',
        options=[{'label': facultad, 'value': facultad} for facultad in data['Facultad'].unique()],
        value='Todas las carreras',
        clearable=False,
        style={'width': '50%', 'margin': 'auto'}
    ),
    dcc.Graph(id='bar-chart', style={'height': '75vh'}),
    dcc.Dropdown(
        id='producto-dropdown',
        options=[{'label': producto, 'value': producto} for producto in productos],
        value=productos[0],
        clearable=False,
        style={'width': '50%', 'margin': 'auto'}
    ),
    dcc.Graph(id='niveles-avance-chart', style={'height': '25vh'})
], style={'height': '100vh'})

# Callback para actualizar los gráficos
@app.callback(
    [Output('bar-chart', 'figure'),
     Output('niveles-avance-chart', 'figure')],
    [Input('facultad-dropdown', 'value'),
     Input('producto-dropdown', 'value')]
)
def update_charts(selected_facultad, selected_producto):
    logger.info(f"Actualizando gráficos para facultad: {selected_facultad}, producto: {selected_producto}")
    if selected_facultad == 'Todas las carreras':
        filtered_data = data[data['Facultad'] != 'Todas las carreras']
    else:
        filtered_data = data[data['Facultad'] == selected_facultad]

    # Ordenar las carreras por orden alfabético e invertir el orden
    filtered_data = filtered_data.sort_values('Carrera', ascending=False)

    # Crear figura principal
    fig = go.Figure()

    # Agregar barras apiladas horizontales con etiquetas personalizadas para `columns_num`
    for idx, col in enumerate(columns_num):
        if col in filtered_data.columns:
            fig.add_trace(go.Bar(
                y=filtered_data['Carrera'],
                x=filtered_data[col],
                name=col,
                marker_color=colors[idx % len(colors)],
                text=filtered_data[columns_cat[idx]],
                texttemplate='%{text}',
                textposition='inside',
                insidetextanchor='middle',  # Centralizar horizontalmente las etiquetas
                textangle=0,  # Etiquetas horizontales
                textfont=dict(size=10),  # Tamaño de letra estandarizado
                orientation='h'  # Orientación horizontal
            ))

    # Personalizar la gráfica principal
    fig.update_layout(
        yaxis_title='Carreras',
        xaxis_title='Nivel de Avance',
        barmode='stack',
        xaxis=dict(
            tickmode='linear',
            dtick=1
        ),
        legend_title='Etapas del Proceso',
        legend=dict(traceorder='reversed'),  # Invertir el orden de la leyenda
        template='plotly_white'
    )

    # Filtrar los niveles de avance por el producto seleccionado
    producto_niveles = niveles_avance[niveles_avance['Producto'] == selected_producto]

    # Crear figura de niveles de avance
    fig_niveles = go.Figure()

    fig_niveles.add_trace(go.Bar(
        y=[selected_producto] * len(producto_niveles),
        x=producto_niveles['Nivel'],
        text=producto_niveles['Descripción nivel de avance'
