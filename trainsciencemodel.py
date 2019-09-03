import tensorflow as tf
from tensorflow import keras
import json
import redditdata as rd
import redditmodelscience as rms
import random
import math
from os import listdir
from os.path import isfile, join

tf.enable_eager_execution()

science_mode_removed_data_dir = 'data/science_removed_comments'
comments = []

trainpercentage = 0.8
validationpercentage = 1 - trainpercentage

files = [f for f in listdir(science_mode_removed_data_dir) if isfile(join(science_mode_removed_data_dir, f))]

#Build the model
model = rms.getmodel()

for filename in files:
    curr_file = join(science_mode_removed_data_dir, filename)
    print(curr_file)
    with open(curr_file, 'r') as f:
        comments = json.load(f)

    if len(comments) == 0:
        continue

    #Prepare data to be fed into the model
    random.shuffle(comments)

    comment_titles = [c['submission_title'] for c in comments]
    comment_texts = [c['text'] for c in comments]
    comment_removed = [c['removed'] for c in comments]

    #Split the data into train and test sets
    comment_title_train = comment_titles[math.floor(len(comment_titles)*trainpercentage):]
    comment_title_test = comment_titles[:math.ceil(len(comment_titles)*validationpercentage)]

    comment_text_train = comment_texts[math.floor(len(comment_texts)*trainpercentage):]
    comment_text_test = comment_texts[:math.ceil(len(comment_texts)*validationpercentage)]

    comment_removed_train = comment_removed[math.floor(len(comment_removed)*trainpercentage):]
    comment_removed_test = comment_removed[:math.ceil(len(comment_removed)*validationpercentage)]

    #Feed the data through the model
    history = model.fit([comment_title_train, comment_text_train],
                            [comment_removed_train], epochs=10)

    #Test the model and print results
    results = model.evaluate([comment_title_test, comment_text_test], [comment_removed_test], verbose=0)
    for name, value in zip(model.metrics_names, results):
        print("%s: %.3f" % (name, value))

model.save_weights(rms.checkpoint_dir)

print("Model saved...")