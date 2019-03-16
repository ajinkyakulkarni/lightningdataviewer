from flask import Flask, render_template, send_from_directory, request, jsonify, g, session, redirect, url_for
from flask_github import GitHub, GitHubError
from github import Github as GithubAPI
import re
import db
import read_data
import helper
import os
import tempfile
import html
import json

app = Flask(__name__)

# Configuration settings
app.config.from_object('config')
cesium_key = app.config['CESIUM_KEY']
data_dir = app.config['DATA_DIR']
date = app.config['DATE']
secret_key = app.config['SECRET_KEY']
repo_owner = app.config['GITHUB_REPO_OWNER']
repo_name = app.config['GITHUB_REPO_NAME']
github_access_token = app.config['GITHUB_ACCESS_TOKEN']
fs_org_code = app.config['FULLSTORY_ORG_CODE']
fs_api_key = app.config['FULLSTORY_API_KEY']

# Setup github-flask
github = GitHub(app)

# Initialize database
db_session, User = db.init_db(app)


@app.route('/')
def index():
    """
    Route for main index page
    """
    return render_template('index.html', data={'date': date, 'cesium_key': cesium_key, 'fs_org_code': fs_org_code})


@app.route('/data')
def data():
    """
    This API endpoint returns data in JSON format to the frontend client
    """
    _, csv_file = tempfile.mkstemp()
    try:
        data_path = os.path.join(app.root_path, data_dir)
        read_data.generate_lightning_csv(data_path, csv_file)
        return helper.csv_to_json(csv_file)
    finally:
        os.remove(csv_file)


@app.route('/favicon.ico')
def favicon():
    """
    API endpoint to return favicon icon
    """

    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.before_request
def before_request():
    """
    This function gets called before each request and it creates the session based on currently logged in user
    """

    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


@app.after_request
def after_request(response):
    """
    This function gets called after each request is finished and cleans up the session
    """

    db_session.remove()
    return response


@github.access_token_getter
def token_getter():
    """
    Helper function to return user's github access token
    """
    user = g.user
    if user is not None:
        return user.github_access_token


@app.route('/github-callback')
@github.authorized_handler
def authorized(access_token):
    """
    This is the callback function that gets called by Github OAuth authenticator.
    This function also stores user's info into the database table for later use
    """

    next_url = request.args.get('next') or url_for('index')

    if access_token is None:
        return redirect(next_url)

    user = User.query.filter_by(github_access_token=access_token).first()

    if user is None:
        user = User(access_token)
        db_session.add(user)

    user.github_access_token = access_token

    g.user = user

    github_user = github.get('/user')

    # Store user's github id, login and email into the database table
    user.github_id = github_user['id']
    user.github_login = github_user['login']
    user.github_email = github_user['email']

    db_session.commit()

    session['user_id'] = user.id

    return redirect(next_url)


@app.route('/login')
def login():
    """
    API endpoint to log user using Github
    """

    if session.get('user_id', None) is None:
        return github.authorize()
    else:
        return 'Already logged in'


@app.route('/logout')
def logout():
    """
    API endpoint to log user out of Github
    """

    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/user')
def user():
    """
    API endpoint to retrieve logged user's info
    """

    try:
        github_user = github.get('/user')
        uid = helper.get_uid(secret_key, github_user["email"])
        return jsonify({"uid": uid, "user": github_user})
    except GitHubError:
        return jsonify({"uid": False})


@app.route('/repo')
def repo():
    """
    API endpoint to retrieve stats about the Github repo where issues would be filed
    """

    return jsonify(github.get(f"/repos/{repo_owner}/{repo_name}"))


@app.route('/fs')
def fullstory_sessions():
    """
    This API endpoint returns the Fullstory session URLs that could be associated with identified Github users.
    Returned session URLs are behind authentication and only owner of the fullstory account can view them.
    This API is used only for internal product improvement purpose.
    """

    fullstory_uids = {}

    # Get all users in the database
    users = User.query.all()

    # Retrieve session URLs using unique uid using Fullstory REST APIs
    for user in users:
        uid = helper.get_uid(secret_key, user.github_email)
        fullstory_uids[uid] = []
        sessions = helper.get_fs_session(uid, fs_api_key)
        session_urls = []
        for session in sessions:
            session_urls.append(session["FsUrl"])
        fullstory_uids[uid] = {"session_urls": session_urls,"issues":[]}

    github_obj = GithubAPI(github_access_token)

    repo = github_obj.get_repo(f"{repo_owner}/{repo_name}")

    # Get all open issues from Github repo
    issues = repo.get_issues(state="open")

    # Iterate through all issues and try to assign them to fullstory session using uid
    for issue in issues:
        if issue.body is not None:
            r1 = re.findall(r"Unique issue identifier: (.*)", issue.body)
            if len(r1) > 0:
                uid_from_issue = r1[0]
                fullstory_uids[uid_from_issue]["issues"].append(issue.html_url)

    return jsonify(fullstory_uids)


@app.route("/issue", methods=['POST'])
def make_github_issue():
    """
    This API endpoint is used to create Github issue using their APIs
    """

    try:
        github_user = github.get('/user')

        github_obj = GithubAPI(github_access_token)
        repo = github_obj.get_repo(f"{repo_owner}/{repo_name}")

        issue_title = html.escape(request.json["issue_title"])
        issue_body = html.escape(request.json["issue_body"])

        # We add additional metadata into the issue body to track the users who submitted the issue
        # So that we can reach back to them with the resolution

        issue_body += "\n\n\n------------ Issue Metadata (DO NOT MODIFY) --------------------"
        uid = helper.get_uid(secret_key, github_user["email"])
        issue_body += "\nUnique issue identifier: " + uid

        if request.json["issue_type"] == "feature":
            label = "enhancement"
        else:
            label = "bug"

        response = repo.create_issue(title=issue_title, body=issue_body, labels=[label])

        return jsonify({"issue_id": response.id})

    except:
        print("Error creating an issue")


if __name__ == '__main__':
    app.run()
