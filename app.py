# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
df = pd.DataFrame()
best_question = ""

def func_entropy(ser):
    p = ser.value_counts(normalize=True)
    return -np.sum(p * np.log2(p))

def ask_question_and_narrow_down(socket, previous_responses={}):
    global df, best_question 
    if len(df) == 1:
        character_name = df['Name'].values[0]
        socket.emit('game_result', {'result': f"The character you are thinking of is: {character_name}"})
        return character_name

    cmis = df.iloc[:, 1:].apply(func_entropy).to_dict()
    if len(set(cmis.values())) == 1:
        names = df['Name'].to_list()
        names_string = ', '.join(names)
        socket.emit('game_result', {'result': f"All remaining characters have the same information gain. The characters you picked are among: {names_string}"})
        return names_string

    best_question = df.iloc[:, 1:].apply(func_entropy).sort_values(ascending=False).head(1).index[0]
    socket.emit('ask_question', {'question': best_question})

@socketio.on('user_response')
def handle_user_response(data):
    global df, best_question  
    response = data['response'].strip().lower()
    previous_responses = data.get('previous_responses', {})
    if response in ['yes', 'no']:
        if response == 'yes':
            df = df[df[best_question] == 1]
        elif response == 'no':
            df = df[df[best_question] == 0]

        socketio.emit('remaining_characters', {'count': len(df)})
        if len(df) <= 10:
            remaining_characters = df['Name'].to_list()
            socketio.emit('remaining_characters', {'characters': remaining_characters})

        ask_question_and_narrow_down(socketio, previous_responses)

@socketio.on('start_game')
def handle_start_game():
    global df, best_question  
    df = pd.read_csv('change_binary_fin.csv')
    emit('game_started', {'message': 'Game started!'})
    ask_question_and_narrow_down(socketio, previous_responses={})
@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    socketio.run(app, debug=True)
