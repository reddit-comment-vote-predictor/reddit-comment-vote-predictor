import datetime
import time, threading
from flask import Flask, request, jsonify, json, send_from_directory
import logging
import redditmodel as rm
import redditmodelgenerative as rmg
import redditmodelscience as rms
import redditdata as rd
import tensorflow as tf
import pickle
import praw
from praw.models import MoreComments
from pymongo import MongoClient
import sys

physical_devices = tf.config.list_physical_devices('GPU') 
try: 
  # Disable first GPU 
  tf.config.set_visible_devices(physical_devices[1:], 'GPU') 
  logical_devices = tf.config.list_logical_devices('GPU') 
  # Logical device was not created for first GPU 
  assert len(logical_devices) == len(physical_devices) - 1 
except: 
  # Invalid device or cannot modify virtual devices once initialized. 
  pass 

SECONDS_IN_MINUTE = 60
MINUTES_IN_HOUR = 60
SECONDS_IN_HOUR = SECONDS_IN_MINUTE * MINUTES_IN_HOUR

#mongodb setup
connection_string = "mongodb://localhost:27017" if len(sys.argv) == 1 else sys.argv[1]
client = MongoClient(connection_string)
db=client["reddit-comment-vote-predictor"]
collection = db.comments

#Mode which predicts votes
model = rm.getmodelandweights()

#Get information to build model which generates text
f = open('settings/char2idx.pckl', 'rb')
char2idx = pickle.load(f)
f.close()

print("Read char2idx from disk")

f = open('settings/idx2char.pckl', 'rb')
idx2char = pickle.load(f)
f.close()

print("Read idx2char from disk")

f = open('settings/vocab.pckl', 'rb')
vocab = pickle.load(f)
f.close()

print("Read vocab from disk")

# Length of the vocabulary in chars
vocab_size = len(vocab)

#Model which generates text
modelgenerative = rmg.getmodel(vocab_size = vocab_size, embedding_dim=rmg.embedding_dim, rnn_units=rmg.rnn_units, batch_size=1)

modelgenerative.load_weights(rmg.checkpoint_dir)

modelgenerative.build(tf.TensorShape([1, None]))

#Model which predicts if a comment will be removed on /r/science
modelscience = rms.getmodelandweights()

commentstoremove = []
obtainedcommentstoremovetime = None

def get_comments_to_remove_timed():
    while True:
        print(time.ctime())
        get_comments_to_remove()
        time.sleep(SECONDS_IN_HOUR)

def get_comments_to_remove():
    global commentstoremove
    global obtainedcommentstoremovetime
    commentstoremove = rms.getpredictedremovedcomments(modelscience)
    obtainedcommentstoremovetime = datetime.datetime.utcnow()

app = Flask(__name__)

@app.before_first_request
def activate_job():
    print("Before first request")
    thread = threading.Thread(target=get_comments_to_remove_timed)
    thread.daemon = True
    thread.start()

@app.route('/', methods=['GET'])
def get_tasks():
    return send_from_directory('html', 'main.html')

@app.route('/api/subreddits', methods=['GET'])
def subreddit_task():
    return jsonify(rd.subreddit_list)

@app.route('/api/predict', methods=['POST'])
def post_predict():
    answer = {}
    content = request.json
    if 'time' in content and 'title' in content and 'text' in content and 'subreddit' in content:
        time = [content['time']]
        title = [content['title']]
        text = [content['text']]
        subreddit = [content['subreddit']]
        if subreddit[0] > 0 and subreddit[0] <= len(rd.subreddit_list):
            predictions = rm.getprediction(model, title, time, subreddit, text, collection)
            answer = {"prediction": predictions[0]}
        else:
            answer = {"error": "Subreddit must be an integer between 1 and " + str(len(rd.subreddit_list))}
    else:
        answer = {"error": "Missing one or more fields. Please provide time, title, text, and subreddit"}
    return jsonify(answer)

@app.route('/api/predict/day', methods=['POST'])
def post_predict_day():
    answer = {}
    content = request.json
    if 'time' in content and 'title' in content and 'text' in content and 'subreddit' in content:
        time = content['time']
        title = content['title']
        text = content['text']
        subreddit = content['subreddit']
        if subreddit > 0 and subreddit <= len(rd.subreddit_list):
            titles, times, subreddits, texts = rd.dailydata(title, time, subreddit, text)
            predictions = rm.getprediction(model, titles, times, subreddits, texts, collection)
            answer = {"times": times, "predictions": predictions}
        else:
            answer = {"error": "Subreddit must be an integer between 1 and " + str(len(rd.subreddit_list))}
    else:
        answer = {"error": "Missing one or more fields. Please provide time, title, text, and subreddit"}
    return jsonify(answer)

@app.route('/api/generate', methods=['POST'])
def post_generate():
    answer = {}
    content = request.json
    if 'text' in content:
        text = content['text']
        generatedtext = rmg.generatesentence(modelgenerative, text, char2idx, idx2char)
        answer = {"generated_text": generatedtext}
    else:
        answer = {"error": "Missing one or more fields. Please provide time, title, text, and subreddit"}
    return jsonify(answer)

@app.route('/api/science/badcomments', methods=['POST'])
def post_predict_removed():
    return jsonify(commentstoremove)

@app.route('/api/science/badcomments/obtainedtime', methods=['GET'])
def post_predict_removed_time():
    return jsonify(obtainedcommentstoremovetime)

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/<path:path>')
def send_app(path):
    return send_from_directory('html', path + '.html')

@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('css', path)

if __name__ == '__main__':
    app.run(debug=True)
