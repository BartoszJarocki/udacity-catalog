Udacity - Item Catalog
============

This is a front-end (HTML, CSS with materialise CSS framework) and back-end (Python with Jinja2) project which provides a catalog funcationality.
Catalog allows regular CRUD operations to create categories and items (after logging in).
Users can login using their Google's account.

## Libraries
Project uses some external libraries like:
1. flask framework
2. sqlalchemy
3. jinja2 templates

## Installing dependencies
1. Install virtualenv run ```pip install virtualenv```.
2. Install all needed dependencies run ```pip install -r requirements.txt```
3. Activate virtualenv run ```source ./bin/activate```

## Running locally
1. Run `python populate_catalog.py` to create database and populate dummy data.
3. Run `python server.py` and check http://localhost:5000

## API
1. `/api/categories/`- Returns categories json.
2. `/api/categories/<int:category_id>`- Returns category items json.
3. `/api/items/<int:item_id>`- Returns item details json.
