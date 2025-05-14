from flask import Flask
from threading import Thread
from waitress import serve  # <- thêm dòng này

app = Flask('')

@app.route('/ping', methods=["GET", "HEAD"])
def home():
    return "Hello. I am alive!", 200

def run():
    serve(app, host="0.0.0.0", port=8080)  # <- dùng waitress thay vì app.run()

def keep_alive():
    t = Thread(target=run)
    t.start()
