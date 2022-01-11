# FastDAC Spectrum Analyzer
# by Anton Cecic

# Required packages:  pyserial, numpy, scipy, plotly, dash, dash_bootstrap_components, dash_extensions, dash_daq, pandas, os, datetime

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
from dash_extensions import Download
from dash_extensions.snippets import send_file
import dash_daq as daq
import pandas as pd
import os
import datetime
from serial.serialutil import SerialException
from dash.exceptions import PreventUpdate
from re import I
import numpy as np
from pathlib import Path
from logging import exception
import matplotlib.animation as animation
import struct
import matplotlib.pyplot as plt
PORT = [0, 'COM4']
DUR = [0,1]
SELAVG = [0, 5]
SELAX = [0, 'log']
CHNL = [0, [0,]]

def make_layout():
    global fig
    fig = make_subplots(rows=[1,2,2,2][len(CHNL[-1])-1], cols=[1,1,2,2][len(CHNL[-1])-1])
    fig.update_layout(title_text=" ", title_x=0.5, legend_title = "channels", template='plotly_dark')
    fig.update_yaxes(type=SELAX[-1], title_text=r'mV<sup>2</sup> / Hz')
    fig.update_xaxes(title_text='Frequency [Hz]')
    fig.update_layout(showlegend=False)
    return fig

make_layout()

def connect():
    global ser
    ser = serial.Serial(PORT[-1], baudrate=1750000, timeout=1)

connect()

def query(command):

        ser.write(command)
        data = ser.readline()
        data = data.decode('ascii', errors='ignore').rstrip('\r\n')
        return data

def IDN():
    return query(b"*IDN?\r")

def READ_CONVERT_TIME(channel=[0,]):
    cmd = "READ_CONVERT_TIME,{}\r".format(channel)
    return query(bytes(cmd, "ascii"))

def READ_MEASURE_FREQ(channels=[0,]):
        convert_time = list()
        for c in channels:
            read_time_bytes = READ_CONVERT_TIME(c)
            time.sleep(0.3)
            read_time = int(read_time_bytes)

            if read_time not in convert_time:
                convert_time.append(read_time)

        c_freq = 1/(convert_time[0]*10**-6)  # Hz
        return c_freq/len(channels)

def ASK_SPEC_ANA(duration, measure_freq, channels=[0,]):

        num_bytes = int(np.round(measure_freq*duration))
        cmd = "SPEC_ANA,{},{}\r".format("".join(str(ch) for ch in channels), num_bytes)
        return ser.write(bytes(cmd,'ascii'))

def two_bytes_to_int(two_bytes, bigEndian=True):

    if bigEndian:
        return struct.unpack(">H", two_bytes)[0]
    else:
        return struct.unpack("<H", two_bytes)[0]

def map_int16_to_mV(int_val):
    return (int_val - 0) * (20000.0) / (65536.0) - 10000.0

def GET_SPEC_ANA():

        voltage_readings = []
        buffer = ser.read(ser.in_waiting)
        stuff = buffer.decode('ascii', errors='ignore').rstrip('\r\n')
        if 'READ_FINISHED' in stuff:
            found = True
        else:
            found = False
        info = [buffer[i:i+2] for i in range(0, len(buffer), 2)]
        for two_bytes in info:
            if len(two_bytes)==2:
                int_val = two_bytes_to_int(two_bytes, bigEndian=True)
                voltage_reading = map_int16_to_mV(int_val)
                voltage_readings.append(voltage_reading)

        return voltage_readings, found

def CALC_SPECTRUM(measure_freq, voltage_readings, channels=[0,]):
    
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

fdid = IDN()
mf = int(READ_MEASURE_FREQ(channels=[0]))
print('mf = ' + str(mf))



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
                    ['Download'], color = '#1e81b0'
                ),
                daq.BooleanSwitch(id="download-switch", on=False), 
                Download(id="download")

            ],
            flush=True,
            style={'margin-top':'15px', 'margin-left': '15px', "margin-right": "15px"}
        ),

        dbc.ListGroup(
            [ 
                dbc.Label(
                    ['FastDAC runtime (s)'], color = '#1e81b0'
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
                    ['Port'], color = '#1e81b0'
                ),
                dbc.Input(
                    id='enter-port', 
                    type='text', 
                    value=str(PORT[-1]), 
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
                children=' ', 
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
                'number of bytes', 
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
        'padding-top':'1%', 
        'padding-bottom':'50%',
        'padding-right':'0%',
        'padding-left':'0%'}

)

voltage_values = []



@app.callback(
    Output(component_id='live-graph', component_property='figure'),
    Output(component_id = 'label0', component_property='children'),
    Output(component_id = 'label1', component_property='children'),
    Output(component_id = 'label2', component_property='children'),
    Output(component_id = 'label3', component_property='children'),
    [Input(component_id='graph-update', component_property='n_intervals'),
    Input("download-switch", "on"),
    Input(component_id='button', component_property='n_clicks'),
    State(component_id='enter-duration', component_property='value'),
    State(component_id='enter-port', component_property='value'),
    State(component_id='channels-checklist', component_property='value'),
    State(component_id='axes-checklist', component_property='value'),
    ]
    )

def callback(input_data, ON, n_clicks, dur, port, channel_arr, selected_axes):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if 'button' in changed_id:
        DUR.append(float(dur))
        SELAX.append(selected_axes)
        CHNL.append(channel_arr)
        PORT.append(port)
        msg = 'loading...'
        make_layout()
        connect()
        global fdid
        fdid = IDN()
        
    else:
        msg = ' '

    if ser.in_waiting==0:
        ASK_SPEC_ANA(DUR[-1], mf, channels=CHNL[-1])

    time.sleep(0.1)
    for j in range(int(DUR[-1] / 0.1 * 0.7)):
        data1 = GET_SPEC_ANA()
        time.sleep(0.1)
        voltage_values.extend(data1[0])
        finished = data1[1]

        
        if finished == True:
            data = CALC_SPECTRUM(mf, voltage_values[int(50*DUR[-1]):int(-50*DUR[-1])], channels=CHNL[-1])
            fig.data = []

            for k in range(len(CHNL[-1])):    
                fig.add_trace(
                    go.Scatter(
                        x=data[0][k][15:-1], 
                        y=data[1][k][15:-1]), 
                        row=[1,2,1,2][k],
                        col=[1,1,2,2][k])

            global num_pts
            num_pts = len(data[0][k])
            voltage_values.clear()

            break

        
    return fig, msg, fdid, DUR[-1], num_pts

if __name__ == '__main__':
    app.run_server(debug=False, use_reloader=False)  
   

    #  app.run_server(debug=False, host='0.0.0.0')  # NEVER use debug=True with host = '0.0.0.0' as it makes the computer vulnerable to attacks
 
