from flask import jsonify
import hmac
import hashlib
import base64
import requests
import csv


def csv_to_json(csv_file):
    """
    Read CSV and output JSON

    :param csv_file: temporary CSV file
    :return:  JSON Response Object
    """
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return jsonify(rows)


def get_uid(secret_key, email):
    """
    This function calcualtes the unique user id
    :param secret_key: APP's secret key
    :param email: Github user's email
    :return: unique uid using HMAC
    """

    dig = hmac.new(bytes(secret_key.encode()), email.encode(), hashlib.sha256).digest()
    uid = base64.b64encode(dig).decode()
    return uid


def get_fs_session(uid, fs_api_key):
    """
    This function retrieves the fullstory sessions associated with user having given uid
    :param uid: unique user id
    :param fs_api_key: fullstory API key
    :return:
    """

    url = f"https://www.fullstory.com/api/v1/sessions"
    r = requests.post(url=url, json={"uid": uid, "limit": 20},
                      headers={'Authorization': 'Basic ' + fs_api_key, "Content-Type": "application/json"})

    # if authorized return session URLs
    if r.status_code == 200:
        return r.json()
    else:
        print("Unauthorized request to Fullstory REST API")
        return []
