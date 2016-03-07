import os

from flask import Flask
import sys

from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User

# from item_catalog import app, ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from werkzeug import secure_filename

from flask import make_response

from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import requests
import json

from flask.ext.seasurf import SeaSurf
# from item_catalog import csrf



# path to store images into a folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app = Flask(__name__)
csrf = SeaSurf(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER










CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu App"


# Connect to the database and create session.
engine = create_engine('sqlite:///restaurant.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Authenication with Google
@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

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

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id


    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['credentials']
    if access_token is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['credentials']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Authenticate with Facebook
@csrf.exempt
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]


    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout, let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


# General Disconnect function to disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showRestaurants'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showRestaurants'))


# Method call to create a user
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session['email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

# Method call to get user info
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

# Method call to get user ID
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Checks if uploading of the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# uploads file to the database
def upload_file(restaurant_id):
    f = request.files['picture_file']
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        directory_path = os.path.join(app.config['UPLOAD_FOLDER'], str(restaurant_id))
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        f.save(os.path.join(directory_path, filename))
    return filename


# xml API endpoint for all restaurants
@app.route('/restaurants.xml', methods=['GET'])
def restaurantXML():
    restaurants = session.query(Restaurant).all()
    restaurant_xml = render_template('restaurants.xml', restaurants=restaurants)
    response = make_response(restaurant_xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

# xml API endpoint for all menu items in a restaurant
@app.route('/restaurants/<int:restaurant_id>/restaurantsmenu.xml', methods=['GET'])
def restaurantsMenuXML(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    restaurantMenu_xml = render_template('restaurantsmenu.xml', restaurant=restaurant, items=items)
    response = make_response(restaurantMenu_xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

# xml API endpoint for a single item
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/menuitem.xml', methods=['GET'])
def menuItemXML(restaurant_id, menu_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    menuItem_xml = render_template('menuitem.xml', restaurant=restaurant, item=item)
    response = make_response(menuItem_xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

# RSS API endpoint for all restaurants
@app.route('/restaurants/restaurantsRSS.xml')
def restaurantRSSFeed():
    restaurants = session.query(Restaurant).all()
    restaurantsRSS = render_template('restaurantsRSS.xml', restaurants=restaurants)
    response = make_response(restaurantsRSS)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response

# RSS API endpoint for all menu items in a restaurant
@app.route('/restaurants/<int:restaurant_id>/menu/menuRSS.xml')
def menuRSSFeed(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    menuRSS = render_template('menuRSS.xml', restaurant=restaurant, items=items)
    response = make_response(menuRSS)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response

# RSS API endpoint for a single item
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/itemRSS.xml')
def menuItemRSSFeed(restaurant_id, menu_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    itemRSS = render_template('itemRSS.xml', restaurant=restaurant, i=item)
    response = make_response(itemRSS)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response


# JSON API endpoint for all menu items in a restaurant
@app.route('/restaurants/<int:restaurant_id>/menu/JSON/')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])

#JSON API endpoint for a single menu item
@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON/')
def menuItemJSON(restaurant_id, menu_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem = item.serialize)

#JSON API endpoint for all restaurants
@app.route('/restaurants/JSON/')
def restaurantJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurant = [r.serialize for r in restaurants])


# Show all restaurants
@app.route('/')
@app.route('/restaurants/')
def showRestaurants():
    restaurants = session.query(Restaurant).order_by(Restaurant.name)
    countRestaurants = session.query(Restaurant).count()
    if 'username' not in login_session:
        return render_template('publicrestaurants.html', restaurants=restaurants)
    else:
        return render_template('restaurants.html', restaurants=restaurants, count=countRestaurants)


# Create a new restaurant
@app.route('/restaurants/new/', methods=['GET', 'POST'])
def newRestaurant():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        new_Restaurant = Restaurant(name=request.form['newrestaurantname'],
            description=request.form['newdescription'], user_id=login_session['user_id'])
        session.add(new_Restaurant)
        session.commit()
        flash("new restaurant created")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('newrestaurant.html')


# Edit an existing restaurant
@app.route('/restaurants/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    editingRestaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editingRestaurant.user_id != login_session['user_id']:
        return """<script>
        function myFunction() {alert('You are not authorized to edit the restaurant.'); 
        window.location.href = '/restaurants';}
        </script>
        <body onload='myFunction()'> """
    if request.method == 'POST':
        if request.form['editrestaurantname']:
            editingRestaurant.name = request.form['editrestaurantname']
        session.add(editingRestaurant)
        session.commit()
        if request.form['editdescription']:
            editingRestaurant.description = request.form['editdescription']
        session.add(editingRestaurant)
        session.commit()
        flash("restaurant has been edited")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('editrestaurant.html', r=editingRestaurant)


# Delete a restaurant
@app.route('/restaurants/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    deletingRestaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if deletingRestaurant.user_id != login_session['user_id']:
        return """<script>
        function myFunction() {alert('You are not authorized to delete the restaurant.'); 
        window.location.href = '/restaurants';}
        </script>
        <body onload='myFunction()'> """
    deleteItemsInRestaurant = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    if request.method == 'POST':
        for item in deleteItemsInRestaurant:
            if item.picture:
                f = os.path.join(app.config['UPLOAD_FOLDER'], str(restaurant_id), item.picture)
                if os.path.exists(f):
                    os.remove(f)
            session.delete(item)
            session.commit()
        session.delete(deletingRestaurant)
        session.commit()
        flash('restaurant has been deleted')
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('deleterestaurant.html', d=deletingRestaurant)


# Show all the menu items in a restaurant
@app.route('/restaurants/<int:restaurant_id>/')
@app.route('/restaurants/<int:restaurant_id>/menu/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
    countMenuItems = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).count()
    creator = getUserInfo(restaurant.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicmenus.html', items=items, creator=creator, restaurant=restaurant)
    else:
        return render_template('menu.html', restaurant=restaurant, items=items, count=countMenuItems, creator=creator)


# Create a new menu item
@app.route('/restaurants/<int:restaurant_id>/new/', methods=['GET','POST'])
def newMenuItem(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if login_session['user_id'] != restaurant.user_id:
        return """<script>
        function myFunction() {alert('You are not authorized to add new item to this restaurant.'); 
        window.location.href = '/restaurants/%d/';}
        </script>
        <body onload='myFunction()'> """ % restaurant_id
    if request.method == 'POST':
        newItem = MenuItem(name = request.form['name'], restaurant_id = restaurant_id, 
            description=request.form['description'], price=request.form['price'], 
            course=request.form['course'], user_id=restaurant.user_id)
        # uploads and saves the file in directory and the name of the file is stored in the database
        if request.files['picture_file']:
            filename = upload_file(restaurant_id)
            savedFile = str(filename)
            newItem.picture = savedFile
        session.add(newItem)
        session.commit()
        flash("new menu item created")
        return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)


# Edit an existing menu item
@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/edit/', methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if login_session['user_id'] != restaurant.user_id:
        return """<script>
        function myFunction() {alert('You are not authorized to edit the item.'); 
        window.location.href = '/restaurants/%d/';}
        </script>
        <body onload='myFunction()'> """ % restaurant_id
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        session.add(editedItem)
        session.commit()
        if request.form['description']:
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        if request.form['course']:
            editedItem.course = request.form['course']
        session.add(editedItem)
        session.commit()
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        if request.files['picture_file']:
            filename = upload_file(restaurant_id)
            savedFile = str(filename)
            editedItem.picture = savedFile
        session.add(editedItem)
        session.commit()
        flash("menu item has been edited")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, i=editedItem)


# Delete a menu Item
@app.route('/restaurants/<int:restaurant_id>/<int:menu_id>/delete/', methods=['GET','POST'])
def deleteMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    deleteItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if login_session['user_id'] != restaurant.user_id:
        return """<script>
        function myFunction() {alert('You are not authorized to delete the item.'); 
        window.location.href = '/restaurants/%d/';}
        </script>
        <body onload='myFunction()'> """ % restaurant_id
    if request.method == 'POST':
        # deletes the picture file if exists
        if deleteItem.picture:
            f = os.path.join(app.config['UPLOAD_FOLDER'], str(restaurant_id), deleteItem.picture)
            if os.path.exists(f):
                os.remove(f)
        session.delete(deleteItem)
        session.commit()
        flash("item has been deleted")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deletemenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, i=deleteItem)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
