from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/', methods=["GET", "HEAD"])
def home():
    return "Hello. I am alive!", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
