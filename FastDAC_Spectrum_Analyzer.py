# FastDAC Live Spectrum Analyzer
# by Anton Cecic

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
import dash_daq as daq
import pandas as pd
import datetime
from serial.serialutil import SerialException
from re import I
import numpy as np

port_i = 'COM8'

PORT = [0, port_i]
DUR = [0, 1]
SELAVG = [0, 5]
SELAX = [0, 'log']
CHNL = [0, [0,]]
MSG = ['','']
CA = [0,1]
mf = 0
num_pts = 0
voltage_bytes = []

ser_open = False

def make_layout():
    global fig
    fig = make_subplots(rows=[1,2,2,2][len(CHNL[-1])-1], cols=[1,1,2,2][len(CHNL[-1])-1])
    fig.update_layout(title_text=" ", title_x=0.5, legend_title = "channels", template='plotly_dark')
    fig.update_yaxes(type=SELAX[-1], title_text=r'mV<sup>2</sup> / Hz')
    fig.update_xaxes(title_text='Frequency [Hz]')
    fig.update_layout(showlegend=False)
    return fig

make_layout()


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

    dbc.Row([
        dbc.Col(
            dbc.Card([
                
                dbc.ListGroup(
                    [
                    dbc.Button('Connect', 
                        id='connect',
                        color="success",
                        n_clicks=0)], 
                        style = {'margin-top':'15px', 
                            'margin-left': '15px', 
                            "margin-right": "15px", 
                            "margin-bottom": "15px"
                            },
                        flush=True,
                        ),
                    
                    
                    
                dbc.ListGroup(
                    [
                    dbc.Button('Kill VISA', 
                        id='stop',
                        color="danger",
                        n_clicks=0)], 
                        style = {'margin-top':'15px', 
                            'margin-left': '15px', 
                            "margin-right": "15px", 
                            "margin-bottom": "15px"
                            },
                        flush=True,
                        ),
                

                dbc.ListGroup(
                    [ 
                        dbc.Label(
                            ['Download'], color = '#1e81b0'
                        ),
                        daq.BooleanSwitch(id="download-switch", on=False), 
                        dcc.Download(id="download")

                    ],
                    flush=True,
                    style={'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px", "margin-bottom": "15px"}
                ),
                
                dbc.ListGroup(
                    [ 
                        dbc.Label(
                            ['Port'], color = '#1e81b0'
                        ),
                        dbc.Input(
                            id='enter-port', 
                            type='text', 
                            value=str(PORT[-1]), 
                            style={'color':'black'}
                        )
                    ],flush=True,
                    style={'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px", "margin-bottom": "15px"}
                ),
                
                dbc.ListGroup(
                    [
                    dbc.Button('OK', 
                        id='port-button', 
                        n_clicks=0)], 
                        style = {'margin-top':'15px', 
                            'margin-left': '15px', 
                            "margin-right": "15px", 
                            "margin-bottom": "15px"},
                        flush=True,
                        ),

                
                            ],
                    style = {
                        'width':'200px',
                        'margin-left':'15px', 
                        }
            )
        ,width={"size": 3}),
        
        dbc.Col(
            dbc.Card([

                dbc.ListGroup(
                    [ 
                        dbc.Label(
                            ['FastDAC runtime (s)'], color = '#1e81b0'
                        ),
                        dbc.Input(
                            id='enter-duration', 
                            type='text', 
                            value=str(DUR[-1]), 
                            style={'color':'black'}
                        )
                    ],flush=True,
                    style={'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px", "margin-bottom": "15px"}
                ),
                
                dbc.ListGroup(
                    [                        
                     dbc.Label(
                            ['Current Amp gain'], color = '#1e81b0'
                        ),                     
                     
                     dcc.Dropdown(
                        id='CA-dropdown', 
                        options=[
                            {'label': 'No I amp', 'value': 1},
                            {'label': '1E5', 'value': 1e5},
                            {'label': '1E6', 'value': 1e6},
                            {'label': '1E7', 'value': 1e7},
                            {'label': '1E8', 'value': 1e8},
                            {'label': '1E9', 'value': 1e9}
                        ], 
                        value=0,
                        style={'display':'inline-block', 'color':'black','width':'100px', }
                    ),], style={'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px", "margin-bottom": "15px"}

                ),

                dbc.ListGroup(
                    [

                    html.Label(
                    "Average over ",
                    style={
                        'color':"#1e81b0", 
                        "margin-right": "15px",
                        'display':'inline-block'}
                    ),

                    dcc.Dropdown(
                        id='avg-dropdown', 
                        options=[
                            {'label': '1', 'value': 1},
                            {'label': '2', 'value': 2},
                            {'label': '3', 'value': 3},
                            {'label': '4', 'value': 4},
                            {'label': '5', 'value': 5},
                            {'label': '6', 'value': 6},
                            {'label': '7', 'value': 7}
                        ], 
                        value=1,
                        style={'display':'inline-block', 'color':'black','width':'50px', }
                    ),
                    html.Label(" cycles", style={'color':"#1e81b0", 'margin-left': '15px'}),
                ], 
                
                style={   
                'display':'inline-block',
                'margin-top':'15px', 
                'margin-left': '15px', 
                "margin-right": "15px"}, 
                
                flush=True
            ),




                dbc.ListGroup(
                    [
                        dbc.Label(
                            ['Show channels: '], color = '#1e81b0'
                        ),

                    dcc.Checklist(
                        id='channels-checklist', 
                        options=[
                            {'label': '0', 'value': 0},
                            {'label': '1', 'value': 1},
                            {'label': '2', 'value': 2},
                            {'label': '3', 'value': 3}
                        ], 
                        inputStyle = {"margin-right": "5px"},
                        labelStyle = {"display":"inline-block", "margin-right": "20px"},    
                        value=[0,],
                        
                    ),
                ],
                flush=True , 
                style={'margin-top':'15px', 
                'margin-left': '15px',
                "margin-right": "15px"}
            ),

                

                dbc.ListGroup(
                    [
                        dbc.Label('Vertical axes:', color = "#1e81b0"),
                        dbc.RadioItems(
                            id='axes-checklist', 
                            options=[
                                {'label': 'log', 'value': 'log'},
                                {'label': 'linear', 'value': 'linear'},
                            ], 
                            value = 'log'
                            
                        ),
                    ], 
                    
                    style = {'margin-top':'15px', 
                    'margin-left': '15px', 
                    "margin-right": "15px"}, 
                    flush=True
                ),

                dbc.ListGroup(
                    [
                    dbc.Button('OK', 
                        id='button', 
                        n_clicks=0)], 
                        style = {'margin-top':'15px', 
                            'margin-left': '15px', 
                            "margin-right": "15px", 
                            "margin-bottom": "15px"},
                        flush=True,
                        ),

                    ],
                    style = {
                        'width':'300px', 
                        'margin-left':'15px', 
                        }
                ), width={"size": 3},),

        dbc.Col(
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
                        children=' ', 
                        id = 'label0',
                        style={'color':'#FF2D00'})],
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
                        'FastDAC runtime (s): ', 
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
                        "margin-right": "15px"}, 
                    flush=True
                ),

                dbc.ListGroup(
                    [
                    
                    dbc.Label(
                        'No. of points / channel', 
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

                dbc.ListGroup(
                    [
                    dbc.Label(
                        'Port: ', 
                        color="#1e81b0",
                        style={
                            'margin-left':'10px',
                            'margin-right':'10px'}),

                    dbc.Label(
                        children=PORT[-1],
                        id = 'label4')
                        ],
                        
                        style={
                            "margin-left": "10px",
                            "margin-right": "15px"}
                )]), width={"size": 3},)
            

            ], className = 'g-0',
            style = {
                'margin-left':'15px',
                }
    )

    ], style={
        'padding-top':'1%', 
        'padding-bottom':'0%',
        'padding-right':'0%',
        'padding-left':'0%'}

)

def connect():
    global ser
    ser = serial.Serial(PORT[-1], baudrate=1750000, timeout=1)

def query(command):

        ser.write(command)
        data = ser.readline()
        data = data.decode('ascii', errors='ignore').rstrip('\r\n')
        return data

def IDN():
    return query(b"*IDN?\r")

def killvisa():
    ser.close()

def READ_CONVERT_TIME(channel=[0,]):
    cmd = "READ_CONVERT_TIME,{}\r".format(channel)
    return query(bytes(cmd, "ascii"))

def READ_MEASURE_FREQ(channels=[0,]):
        convert_time = list()
        for c in channels:
            read_time_bytes = READ_CONVERT_TIME(c)
            time.sleep(0.1)
            read_time = int(read_time_bytes)

            if read_time not in convert_time:
                convert_time.append(read_time)

        c_freq = 1/(convert_time[0]*10**-6)  # Hz
        return c_freq/len(channels)

def ASK_SPEC_ANA(duration, measure_freq, channels=[0,]):

        num_bytes = int(np.round(measure_freq*duration))
        cmd = "SPEC_ANA,{},{}\r".format("".join(str(ch) for ch in channels), num_bytes)
        return ser.write(bytes(cmd,'ascii'))

def GET_SPEC_ANA():

        INFO = []
        buffer = ser.read(ser.in_waiting)
        stuff = buffer.decode('ascii', errors='ignore').rstrip('\r\n')
        if 'READ_FINISHED' in stuff:
            found = True
            buffer = buffer[0:-15]
            ser.reset_input_buffer()
        else:
            found = False
        INFO.extend(buffer)
        #print(info)
        # print(INFO)
        return INFO, found

def CALC_SPECTRUM(measure_freq, bytes_arr, CA_gain=1, channels=[0,]):
    # print(bytes_arr)
    voltage_readings = []
    pairs_bytes_arr = [bytes_arr[i:i+2] for i in range(0, len(bytes_arr), 2)]
    
    if not len(pairs_bytes_arr) % 2 == 0:
        #bytes_arr = bytes_arr[0:-1]
        print(bytes_arr)
        print('!')

    for two_bytes in pairs_bytes_arr:
        if len(two_bytes) % 2 == 0:
            int_val = int.from_bytes(two_bytes, 'big')
            voltage_reading = (int_val - 0) * (20000.0) / (65536.0) - 10000.0
            voltage_readings.append(voltage_reading/CA_gain)
            
        else:
            print('!!')
            print(two_bytes)
        
    
    X = []
    Y = []

    channel_readings = {ac: list() for ac in channels}
        
    for k in range(len(channels)):
        channel_readings[k] = voltage_readings[k::len(channels)]
        channel_readings[k] = np.array(channel_readings[k])

        f, Pxx_den = signal.periodogram(channel_readings[k], measure_freq)
        X.append(f)
        Y.append(Pxx_den)

    return X, Y


@app.callback(
    Output(component_id='live-graph', component_property='figure'),
    Output(component_id = 'label0', component_property='children'),
    Output(component_id = 'label1', component_property='children'),
    Output(component_id = 'label2', component_property='children'),
    Output(component_id = 'label3', component_property='children'),
    Output(component_id = 'label4', component_property='children'),
    [Input(component_id='graph-update', component_property='n_intervals'),
    Input("download-switch", "on"),
    Input(component_id='stop', component_property='n_clicks'),
    Input(component_id='connect', component_property='n_clicks'),
    Input('port-button', component_property='n_clicks'),
    Input(component_id='button', component_property='n_clicks'),
    State(component_id='enter-duration', component_property='value'),
    State(component_id='avg-dropdown', component_property='value'),
    State(component_id='channels-checklist', component_property='value'),
    State(component_id='axes-checklist', component_property='value'),
    State(component_id='CA-dropdown', component_property='value'),
    State(component_id='enter-port', component_property='value'),
    ]
    )

def callback(input_data, ON, n_clicks, n_clicks1, n_clicks2, n_clicks3, dur, selected_avg, channel_arr, selected_axes, CA_gain, port):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    
    global ser_open
    global fdid
    global mf
    global X, Y
    
    if ser_open==False:
        try:
            connect()
            ser_open = True
            
            fdid = IDN()
            mf = int(READ_MEASURE_FREQ(channels=[0]))
            X = [[],[],[],[]]
            Y = [[],[],[],[]]
            
        except SerialException:
            print('')
            MSG.append('- Try different port\n')
            print('')
            exit()
    
    if 'connect' in changed_id:
        connect()
        MSG.append('FastDAC connected\n')
        
    if 'button' in changed_id:
        DUR.append(float(dur))
        SELAX.append(selected_axes)
        CHNL.append(channel_arr)
        PORT.append(port)
        SELAVG.append(selected_avg)
        CA.append(CA_gain)

        
        X[0] = []
        X[1] = []
        X[2] = []
        X[3] = []
        Y[0] = []
        Y[1] = []
        Y[2] = []
        Y[3] = []
        make_layout()
        
        if not CA[-1] == 1:
            fig.update_yaxes(type=SELAX[-1], title_text=r'mA<sup>2</sup> / Hz')
        else:
            fig.update_yaxes(type=SELAX[-1], title_text=r'mV<sup>2</sup> / Hz')
        
        if not port == PORT[-1]:
            connect()
            fdid = IDN()
        print('loading changes...')

    if not fdid[0:7] == 'DAC-ADC':
        MSG.append('Try different port')
        connect()

    if not PORT[-1] == str(ser.port):
        MSG.append('Try different port')

    else:
        MSG.append('')

    if ser.in_waiting==0:
        ASK_SPEC_ANA(DUR[-1], mf, channels=CHNL[-1])

    time.sleep(0.05)

    for j in range(11):
        data1 = GET_SPEC_ANA()
        time.sleep(0.1)
        voltage_bytes.extend(data1[0])
        finished = data1[1]
        if finished == True:
            break

    if finished == True:

        data = CALC_SPECTRUM(mf, voltage_bytes, CA[-1], channels=CHNL[-1])
        fig.data = []
        


        for k in range(len(CHNL[-1])):

            try:
                X[k].append(data[0][k][0:len(X[k][-1])])
                Y[k].append(data[1][k][0:len(X[k][-1])])
            except IndexError:
                X[k].append(data[0][k])
                Y[k].append(data[1][k])

            if len(X[k])<SELAVG[-1] and len(X[k])>0:

                xnew=np.mean(X[k], axis=0)
                ynew=np.mean(Y[k], axis=0)

                fig.add_trace(
                    go.Scatter(
                        x=xnew[15:], 
                        y=ynew[15:]),
                        row=[1,2,1,2][k],
                        col=[1,1,2,2][k])

                del xnew, ynew


            elif SELAVG[-1]==1:
                xnew=data[0][k][15:]
                ynew=data[1][k][15:]


                fig.add_trace(
                    go.Scatter(
                        x=xnew[15:], 
                        y=ynew[15:]), 
                        row=[1,2,1,2][k],
                        col=[1,1,2,2][k])
                
                del xnew, ynew


            elif len(X[k][-1]) == len(X[k][-SELAVG[-1]]):
                xnew=np.mean(X[k][-SELAVG[-1]:-1], axis=0)
                ynew=np.mean(Y[k][-SELAVG[-1]:-1], axis=0)

                fig.add_trace(
                    go.Scatter(
                        x=xnew[15:], 
                        y=ynew[15:]), 
                        row=[1,2,1,2][k],
                        col=[1,1,2,2][k])

                del xnew, ynew

            else:
                MSG.append('ERROR:  Attempting to combine different size arrays')

            if ON == True:
                dt = datetime.datetime.now()
                fig.write_html('Desktop/Spectrum_Ch{}_date{}-{}-{}_time{}{}.html'.format(CHNL[-1][k],dt.year, dt.month, dt.day, dt.hour, dt.minute))
                d = {'Frequency (Hz)': data[0][k][15:], 'mV*mV/Hz': data[1][k][15:]}
                df = pd.DataFrame(data=d)
                df.to_csv('Desktop/Spectrum_Ch{}_date{}-{}-{}_time{}{}.csv'.format(CHNL[-1][k],dt.year, dt.month, dt.day, dt.hour, dt.minute), index=False)
        
        global num_pts
        num_pts = len(data[0][k])
        
        voltage_bytes.clear()
        
    if 'stop' in changed_id:
        killvisa()
        MSG.append('FastDAC disconnected\n')
    
        
    return fig, MSG[-1], fdid, DUR[-1], num_pts, str(ser.port)

if __name__ == '__main__':
    app.run_server(debug=False, use_reloader=False)  
    
    
