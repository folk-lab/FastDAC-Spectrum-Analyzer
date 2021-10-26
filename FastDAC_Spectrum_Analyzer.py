# FastDAC Spectrum Analyzer
# by Anton Cecic

from re import template
import time
import serial
import numpy as np
from scipy import signal
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash import html
from dash import dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

def PSD(port, baudrate, duration, channels=[0, ]):

    s = serial.Serial(port, baudrate, timeout=1)        # Fibre optic connection

    def Query(command):

        if not s.is_open:
            s.open()
        s.write(command)
        data = s.readline()
        data = data.decode('ascii', errors='ignore').rstrip('\r\n')
        s.close()
        return data

    FastDAC_ID = Query(b"*IDN?\r")

    ts = time.time()
    xper = []
    yper = []

    convert_time = list()
    for c in channels:
        cmd = bytes("READ_CONVERT_TIME,{}\r".format(c), 'ascii')
        read_time_bytes = Query(cmd)
        read_time = int(read_time_bytes)

        if read_time not in convert_time:
            convert_time.append(read_time)

    c_freq = 1/(convert_time[0]*10**-6)  # Hz
    measure_freq = c_freq/len(channels)
    num_bytes = int(np.round(measure_freq*duration))

    cmd = "SPEC_ANA,{},{}\r".format("".join(str(ch) for ch in channels), num_bytes)

    if not s.is_open:
        s.open()
    s.write(bytes(cmd,'ascii'))

    channel_readings = {ac: list() for ac in channels}
    voltage_readings = []
    try:
        while s.in_waiting > 240 or len(voltage_readings) <= num_bytes/2:
            buffer = s.read(240)
            info = [buffer[i:i+2] for i in range(0, len(buffer), 2)]
            for two_bytes in info:
                int_val = int.from_bytes(two_bytes, 'big')
                voltage_reading = (int_val - 0) * (20000.0) / (65536.0) - 10000.0
                voltage_readings.append(voltage_reading)
    except:
        s.close()
        raise

    s.close()

    for k in range(0, len(channels)):
        channel_readings[k] = voltage_readings[k::len(channels)]
        channel_readings[k] = np.array(channel_readings[k])

        f, Pxx_den = signal.periodogram(channel_readings[k], measure_freq)
        xper.append([f])
        yper.append([Pxx_den])

    return xper, yper, str(num_bytes), str(time.time() - ts), FastDAC_ID


X = [[],[],[],[]]
Y = [[],[],[],[]]
PORT = [0,'COM3']
BR = [0,1750000]
DUR = [0,1.5]
SELAVG = [0, 5]
SELAX = [0, 'log']
CHNL = [0, [0]]

#app = dash.Dash(__name__)
app = dash.Dash(external_stylesheets=[dbc.themes.DARKLY])

app.layout = html.Div(
    [

    html.Div([

        html.Div([
            dcc.Graph(id="live-graph", 
                animate=True)

            ], style={'width': '75%', 
            'height':'100%', 
            'margin-left': '15px', 
            'margin-top': '15px', 
            'margin-bottom': '15px', 
            'border': '3px black solid'}
            ),

            dcc.Interval(id="graph-update", 
                interval=1500, 
                n_intervals=0)]),

    dbc.Card([

        dbc.ListGroup(
            [ 
                dbc.Label(
                    ['Port:'], color = '#1e81b0'
                ),
                dbc.Input(
                    id='enter-port', 
                    type='text', 
                    value=str(PORT[-1]), 
                    style={'color':'white'}
                )
            ],
            flush=True,
            style={'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px"}
        ),

        dbc.ListGroup(
            [
                dbc.Label('Connection:', color = "#1e81b0"),
                dbc.RadioItems(
                    id='usb-checklist', 
                    options=[
                        {'label': 'USB', 'value': 57600},
                        {'label': 'Fibre Optic', 'value': 1750000},
                    ], 
                    value = 1750000
                    
                ),
            ], style = {'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px"}, flush=True
        ),

        dbc.ListGroup(
            [ 
                dbc.Label(
                    ['Duration:'], color = '#1e81b0'
                ),
                dbc.Input(
                    id='enter-duration', 
                    type='text', 
                    value=str(DUR[-1]), 
                    style={'color':'white'}
                )
            ],flush=True,
            style={'margin-top':'15px', 'margin-left': '15px',"margin-right": "15px"}
        ),

        dbc.ListGroup(
            [
                dbc.Label(
                    ['Show channels: '], color = '#1e81b0'
                ),

            dbc.Checklist(
                id='channels-checklist', 
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                    {'label': '3', 'value': 3}
                ], 
                    
                value=[0],
                
            ),
        ]  ,flush=True , style={'margin-top':'15px', 'margin-left': '15px',"margin-right": "15px"}
    ),

        dbc.ListGroup(
            [
            dbc.RadioItems(
                id='avg-checklist', 
                options=[
                    {'label': 'Average over 0 cycles', 'value': 0},
                    {'label': 'Average over 1 cycles', 'value': 1},
                    {'label': 'Average over 2 cycles', 'value': 2},
                    {'label': 'Average over 3 cycles', 'value': 3},
                    {'label': 'Average over 4 cycles', 'value': 4},
                    {'label': 'Average over 5 cycles', 'value': 5},
                    {'label': 'Average over 6 cycles', 'value': 6},
                    {'label': 'Average over 7 cycles', 'value': 7}
                ], 

                
                    
                value=5,
                
            ),
        ] , style={'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px"}, flush=True
    ),

        dbc.ListGroup(
            [
                dbc.Label('Vertical axes:', color = "#1e81b0"),
                dbc.RadioItems(
                    id='axes-checklist', 
                    options=[
                        {'label': 'log', 'value': 'log'},
                        {'label': 'linear', 'value': 'lin'},
                    ], 
                    value = 'log'
                    
                ),
            ], style = {'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px"}, flush=True
        ),

        dbc.ListGroup(
            [
            dbc.Button('OK', 
                id='button', 
                n_clicks=0)], 
                style = {'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px", "margin-bottom": "15px"},
                flush=True,
                )
            ],
            style = {
                'width':'25%',
                'height':'25%',
                'margin-left':'15px', 
                'display': 'inline-block'}
        ),

    dbc.Card(
        [

        dbc.ListGroup(
            [
            dbc.Label(
                'Message: ', 
                color="#1e81b0",
                style={
                    'margin-right':'10px'}),

            dbc.Label(
                children='-', 
                id = 'label0')],
                style={
                    "margin-top": "15px", 
                    "margin-left": "15px", 
                    "margin-right": "15px"}, flush=True
        ),

        dbc.ListGroup(
            [
            dbc.Label(
                'FastDAC ID: ', 
                color="#1e81b0",
                style={
                    'margin-right':'15px'}),

            dbc.Label(
                children='-', 
                id = 'label1')
                ], flush=True,
                style={
                "margin-left": "15px", 
                "margin-right": "15px"}
        ),

        dbc.ListGroup(
            [
            dbc.Label(
                'Runtime (s): ', 
                color="#1e81b0",
                style={
                    'margin-right':'15px'}
                    ),

            dbc.Label(
                children='-', 
                id = 'label2')
            ],  
            style={
                "margin-left": "15px", 
                "margin-right": "15px"}, flush=True
        ),

        dbc.ListGroup(
            [
            
            dbc.Label(
                'bytes / cycle / channel: ', 
                color="#1e81b0",
                style={
                'margin-right':'15px'}
                ),

            dbc.Label(
                children='-', 
                
                id = 'label3', 
                style={'textAlign': 'left', 
                'margin-right':'15px'}
                )
            ], flush=True,

            style={
                "margin-left": "15px", 
                "margin-right": "15px",
                }),

            ], style={
                'vertical-align':'top', 
                'display': 'inline-block', 
                'margin-left':'15px', 
                'height':'35%', 
                'width':'48.5%'})

    ], style={
        #'backgroundColor':'#BFBAB9', 
        'padding-top':'1%', 
        'padding-bottom':'50%',
        'padding-right':'0%',
        'padding-left':'0%'}
        
)

@app.callback(
    Output(component_id='live-graph', component_property='figure'),
    Output(component_id='graph-update', component_property='interval'),
    Output(component_id = 'label0', component_property='children'),
    Output(component_id = 'label1', component_property='children'),
    Output(component_id = 'label2', component_property='children'),
    Output(component_id = 'label3', component_property='children'),
    [Input(component_id='graph-update', component_property='n_intervals'),
    Input(component_id='usb-checklist', component_property='value'),
    Input(component_id='avg-checklist', component_property='value'),
    Input(component_id='axes-checklist', component_property='value'),
    Input(component_id='channels-checklist', component_property='value'),
    Input(component_id='button', component_property='n_clicks'),
    State(component_id='enter-port', component_property='value'),
    State(component_id='enter-duration', component_property='value')]
    )

def update_graph(input_data, baudrate, selected_avg, selected_axes, channel_arr, n_clicks, port, dur):

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if 'button' in changed_id:
        PORT.append(port)
        BR.append(baudrate)
        DUR.append(dur)
        SELAVG.append(selected_avg)
        SELAX.append(selected_axes)
        CHNL.append(channel_arr)
        msg = 'loading...'
    else:
        msg = '-'

    psd = PSD(str(PORT[-1]), str(BR[-1]), float(DUR[-1])*2/3, CHNL[-1])

    fig = make_subplots(rows=[1,2,2,2][len(CHNL[-1])-1], cols=[1,1,2,2][len(CHNL[-1])-1])
    fig.update_layout(title_text="FastDAC Spectrum Analyzer", title_x=0.5, legend_title = "channels", template='plotly_dark')
    fig.update_yaxes(type=SELAX[-1], title_text='mV*mV / Hz')
    fig.update_xaxes(title_text='Frequency [Hz]')
    fig.update_layout(showlegend=False)

    for k in range(0, len(CHNL[-1])):
        X[k].append(psd[0][k][0])
        Y[k].append(psd[1][k][0])

        
        if len(X[k])<SELAVG[-1]:
            xnew=np.mean(X[k][-len(X[k]):-1], axis=0)
            ynew=np.mean(Y[k][-len(X[k]):-1], axis=0)

            fig.add_trace(
                go.Scatter(
                    x=xnew[15:], 
                    y=ynew[15:], 
                    name=str(CHNL[-1][k])), 
                    row=[1,2,1,2][k],
                    col=[1,1,2,2][k])

        elif SELAVG[-1]==1:
            xnew=psd[0][k][0]
            ynew=psd[1][k][0]

            fig.add_trace(
                go.Scatter(
                    x=xnew[15:], 
                    y=ynew[15:], 
                    name=str(CHNL[-1][k])), 
                    row=[1,2,1,2][k],
                    col=[1,1,2,2][k])
            
        elif len(X[k][-1]) != len(X[k][-SELAVG[-1]]):
            msg = 'loading...'

        else:
            xnew=np.mean(X[k][-SELAVG[-1]:-1], axis=0)
            ynew=np.mean(Y[k][-SELAVG[-1]:-1], axis=0)
            msg = '-'

            fig.add_trace(
                go.Scatter(
                    x=xnew[15:], 
                    y=ynew[15:], 
                    name=str(CHNL[-1][k])), 
                    row=[1,2,1,2][k],
                    col=[1,1,2,2][k])

    return fig, 1500*float(dur), msg, psd[4], psd[3], psd[2]

if __name__ == '__main__':
     app.run_server(host= '0.0.0.0', debug=True)
