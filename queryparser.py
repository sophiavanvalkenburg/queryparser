"""
queryparser.py
author: Sophia van Valkenburg

This script retrieves a query string, user, and password.
If the user and password are correct, parse the query and
return a JSON string of the parsed values.

"""
from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/parse')
def receive_parse_request():
    if request.method == "GET":
        query_text = request.args.get('text')
        user = request.args.get('user')
        auth = request.args.get('auth')
        if not query_text or not user or not auth:
            response = {
                    "error": "must specify 'text', 'user', and 'auth' fields"
                    }
        else:
            if authenticate(user, auth):
                response = parse(query_text)
            else:
                response = {"error": "user or password is incorrect" }
        return json.dumps(response)
    else:
        return ""

def authenticate(user, auth):
    return True

def parse(query_text):
    return { "content": query_text }

if __name__ == "__main__":
    app.debug = True
    app.run()
