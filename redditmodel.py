import tensorflow as tf
from tensorflow import keras
from datetime import datetime
import tensorflow_hub as hub
import redditdata as rd
import json

def getmodel():
    dropoutrate = 0.3

    hub_layer1 = hub.KerasLayer("https://tfhub.dev/google/tf2-preview/gnews-swivel-20dim/1", output_shape=[20],
                           input_shape=[], dtype=tf.string, trainable=True)
    hub_layer2 = hub.KerasLayer("https://tfhub.dev/google/tf2-preview/gnews-swivel-20dim/1", output_shape=[20],
                           input_shape=[], dtype=tf.string, trainable=True)

    # the first branch operates on the first input
    # This is the context of the comment, namely:
    # minute, hour, day, month, weekday, subreddit
    inputA = keras.Input(shape=(6,))
    x = keras.layers.Dense(6, activation="relu")(inputA)
    x = keras.Model(inputs=inputA, outputs=x)

    # the second branch opreates on the second input
    # This is the post's title
    y = keras.Sequential()
    y.add(hub_layer1)

    # the third branch opreates on the third input
    # This is the comment's text contents, in plaintext
    z = keras.Sequential()
    z.add(hub_layer2)

    # combine the output of the two branches
    combined = keras.layers.concatenate([x.output, y.output, z.output])

    # Build the intermediate layers
    zz = keras.layers.Dense(46, activation="relu")(combined)
    zz = keras.layers.Dropout(dropoutrate)(zz)
    zz = keras.layers.Dense(46, activation="relu")(zz)
    zz = keras.layers.Dropout(dropoutrate)(zz)
    zz = keras.layers.Dense(46, activation="relu")(zz)
    zz = keras.layers.Dropout(dropoutrate)(zz)
    zz = keras.layers.Dense(46, activation="relu")(zz)
    zz = keras.layers.Dropout(dropoutrate)(zz)
    zz = keras.layers.Dense(46, activation="relu")(zz)
    zz = keras.layers.Dropout(dropoutrate)(zz)
    zz = keras.layers.Dense(46, activation="relu")(zz)
    zz = keras.layers.Dropout(dropoutrate)(zz)
    zz = keras.layers.Dense(1, activation="linear")(zz)

    # our model will accept the inputs of the three branches and
    # then output a single value
    model = keras.Model(inputs=[x.input, y.input, z.input], outputs=zz)

    model.summary()

    optimizer = keras.optimizers.Adam()

    model.compile(loss='mse',
        optimizer=optimizer,
        metrics=['mae', 'mse'])
    
    return model

def getmodelandweights():
    model = getmodel()

    model.load_weights('./checkpoints/my_checkpoint')

    return model

def getprediction(model, titles, times, subreddits, texts):
    contexts = [[datetime.utcfromtimestamp(time).minute,
                    datetime.utcfromtimestamp(time).hour,
                    datetime.utcfromtimestamp(time).day,
                    datetime.utcfromtimestamp(time).month,
                    rd.convertutctoweekdayint(time),
                    subreddit] for time, subreddit in zip(times, subreddits)]

    #Build data pipeline
    dataset_context = tf.data.Dataset.from_tensors(contexts)
    dataset_title = tf.data.Dataset.from_tensors(titles)
    dataset_text = tf.data.Dataset.from_tensors(texts)
    dataset_inputs = tf.data.Dataset.zip((dataset_context, dataset_title, dataset_text))
    dataset = tf.data.Dataset.zip((dataset_inputs,))

    return rd.removedecimals(rd.flatten(model.predict(dataset)))
