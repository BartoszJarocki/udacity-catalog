from flask import Flask, render_template as flask_render, request, redirect, url_for, jsonify, flash, make_response, session as login_session
from flask_cors import CORS
import random
import string
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Category, Item, User
from database_setup import Base
from oauth2client import client, crypt
from apiclient import discovery
import httplib2
import json
import requests
from functools import wraps

app = Flask(__name__)
CORS(app)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']


def render_template(template_name, **params):
    params['logged_in'] = 'username' in login_session
    return flask_render(template_name, **params)


def login_required(f):
    """
    Decorator function used to secure pages available only for logged in users.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            flash('Only authenticated users can access item edit form', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login')
def login():
    """
    Shows login view with Google Auth.
    """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', state=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    Performs the Google Auth using oAuth and information from user's
    account. Creates a new session and store values like user_id and name.
    """

    # If this request does not have `X-Requested-With` header, this could be a
    # CSRF
    if not request.headers.get('X-Requested-With'):
        response = make_response(json.dumps('Invalid state'), 403)
        response.headers['Content-type'] = 'application/json'
        return response

    auth_code = request.data
    CLIENT_SECRET_FILE = 'client_secret.json'

    # Exchange auth code for access token, refresh token, and ID token
    credentials = client.credentials_from_clientsecrets_and_code(
        CLIENT_SECRET_FILE, ['profile', 'email'],
        auth_code)

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = get_user_id(login_session['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    response = make_response(json.dumps('User was logged in!'), 200)
    response.headers['Content-Type'] = 'application/json'

    return response


@app.route('/logout')
def logout():
    """
    Revokes the Google Auth using oAuth and information from user's
    account and deletes all the information from the session.
    """
    access_token = login_session['access_token']

    # if there's no access token just redirect to main page
    if access_token is None:
        return redirect(url_for('catalog'))

    # revoke if present
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        print "Token revoked."

    # clear the session
    del login_session['access_token']
    del login_session['email']
    del login_session['username']
    del login_session['picture']

    # show main page
    return redirect(url_for('catalog'))


@app.route('/')
def catalog():
    """
    Shows the main page with categories and 10 latest items added.
    """
    latest_items = session.query(Item).order_by(
        'created_at desc').limit(12).all()
    categories = session.query(Category).all()
    return render_template(
        'main.html',
        categories=categories,
        recent_items=latest_items)


@app.route('/api/categories/')
def api_categories():
    """
    Return the list of categories as JSON.
    """
    categories = session.query(Category).all()
    return jsonify(categories=[category.serialize for category in categories])


@app.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    """
    Renders the form to create a new category and save it in database if all the
    information was entered correctly.
    """
    if request.method == 'POST':
        new_category = Category(
            title=request.form['title'], user_id=login_session['user_id'])
        session.add(new_category)
        flash('Category %s successfully created!' % new_category.title)
        session.commit()
        return redirect(url_for('catalog'))
    else:
        return render_template('new_category.html')


@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """
    Renders the form to edit a specific category and save it in database if all
    the information was entered correctly.
    """
    user_id = login_session['user_id']
    edited_category = session.query(
        Category).filter_by(id=category_id).one()

    if not edited_category.user_id == user_id:
        return redirect(url_for('catalog'))

    if request.method == 'POST':
        if request.form['title']:
            edited_category.title = request.form['title']
        session.add(edited_category)
        flash("Category has been edited")
        session.commit()
        return redirect(url_for('catalog'))
    else:
        return render_template(
            'edit_category.html',
            category=edited_category)


@app.route('/categories/<int:category_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_category(category_id):
    """
    Renders the form to delete a specific category and delete it from database.
    """
    user_id = login_session['user_id']
    category_to_delete = session.query(
        Category).filter_by(id=category_id).one()

    if not category_to_delete.user_id == user_id:
        return redirect(url_for('catalog'))

    if request.method == 'POST':
        session.delete(category_to_delete)
        session.commit()
        flash("Category has been deleted!")
        return redirect(url_for('catalog'))
    else:
        return render_template(
            'delete_category.html',
            category=category_to_delete)


@app.route('/categories/<int:category_id>')
def category_items(category_id):
    """
    Renders the items from given category as JSON.
    """
    category = session.query(
        Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id)
    is_owner = category.user_id == get_session_user_id()
    return render_template(
        'category_items.html',
        category=category,
        items=items,
        is_owner=is_owner)


@app.route('/api/categories/<int:category_id>')
def api_category_items(category_id):
    """
    Return the list of items in given category
    """
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(items=[item.serialize for item in items])

@app.route('/categories/<int:category_id>/items/<int:item_id>')
def item_details(category_id, item_id):
    """
    Renders the item with given item_id.
    """
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(Item).filter_by(id=item_id).one()
    is_owner = item.user_id == get_session_user_id()
    return render_template(
        'item_details.html', category=category, item=item, is_owner=is_owner)


@app.route('/api/items/<int:item_id>')
def api_item_details(item_id):
    """
    Return the details of item with given id as JSON
    """
    try:
        item = session.query(Item).filter_by(id=item_id).one()
        return jsonify(item.serialize)
    except BaseException:
        return make_response(json.dumps('Invalid item id!'), 404)


@app.route('/categories/<int:category_id>/new', methods=['GET', 'POST'])
@login_required
def new_item(category_id):
    """
    Renders the form to create a new item for a category and save it in
    database if all the information was entered correctly.
    """
    category = session.query(Category).filter_by(id=category_id).one()
    user_id = login_session['user_id']
    if request.method == 'POST':
        new_item = Item(title=request.form['title'],
                        description=request.form['description'],
                        category_id=category_id,
                        user_id=user_id)
        session.add(new_item)
        session.commit()
        flash("Item has been created!")
        return redirect(url_for('category_items', category_id=category_id))
    else:
        return render_template(
            'new_item.html',
            category_id=category_id)


@app.route('/categories/<int:category_id>/<int:item_id>/edit',
           methods=['GET', 'POST'])
@login_required
def edit_item(category_id, item_id):
    """
    Renders the form to edit a specific item and save it in database if all
    the information was entered correctly.
    """
    user_id = login_session['user_id']
    edited_item = session.query(Item).filter_by(id=item_id).one()

    if not edited_item.user_id == user_id:
        return redirect(url_for('catalog'))

    if request.method == 'POST':
        if request.form['title']:
            edited_item.title = request.form['title']
        if request.form['description']:
            edited_item.description = request.form['description']
        session.add(edited_item)
        flash("Item has been edited!")
        session.commit()
        return redirect(url_for('category_items', category_id=category_id))
    else:
        return render_template(
            'edit_item.html',
            category_id=category_id,
            item=edited_item)


@app.route('/categories/<int:category_id>/<int:item_id>/delete',
           methods=['GET', 'POST'])
@login_required
def delete_item(category_id, item_id):
    """
    Renders the form to delete a specific item and delete it from database.
    """
    user_id = login_session['user_id']
    item_to_delete = session.query(Item).filter_by(id=item_id).one()

    if not item_to_delete.user_id == user_id:
        return redirect(url_for('catalog'))

    if request.method == 'POST':
        session.delete(item_to_delete)
        session.commit()
        flash("Item has been deleted!")
        return redirect(url_for('category_items', category_id=category_id))
    else:
        return render_template(
            'delete_item.html',
            category_id=category_id,
            item=item_to_delete)


# Helper methods for creating/getting user info
def create_user(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_user_info(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def get_user_id(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except BaseException:
        return None


def get_session_user_id(): 
    try:
         return login_session['user_id']
    except Exception:
         return -1


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
