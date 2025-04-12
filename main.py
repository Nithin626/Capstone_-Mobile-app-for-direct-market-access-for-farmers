from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import hashlib
import tensorflow as tf
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'your_database_name'

mysql = MySQL(app)

# Create database and table if not exists
@app.before_first_request
def create_tables():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(50) NOT NULL,
            password VARCHAR(50) NOT NULL,
            role VARCHAR(20) NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description VARCHAR(200) NOT NULL,
            price FLOAT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            consumer_id INT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (consumer_id) REFERENCES users(id)
        )
    ''')
    mysql.connection.commit()
    cursor.close()

# Load pre-trained models
disease_model = load_model('crop_disease_model.h5')
recommendation_model = RandomForestClassifier()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password
        hash = password + app.secret_key
        hash = hashlib.sha1(hash.encode()).hexdigest()
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, hash,))
        account = cursor.fetchone()
        
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['role'] = account['role']
            return 'Logged in successfully!'
        else:
            msg = 'Incorrect username/password!'
    return render_template('login.html', msg=msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'role' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        
        # Hash the password
        hash = password + app.secret_key
        hash = hashlib.sha1(hash.encode()).hexdigest()
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s, %s)', (username, email, hash, role,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    return render_template('register.html', msg=msg)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST' and 'name' in request.form and 'description' in request.form and 'price' in request.form:
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO products VALUES (NULL, %s, %s, %s)', (name, description, price,))
        mysql.connection.commit()
        return 'Product added successfully!'
    return render_template('add_product.html')

@app.route('/predict_disease', methods=['GET', 'POST'])
def predict_disease():
    if request.method == 'POST':
        image_file = request.files['image']
        img = Image.open(image_file)
        img = img.resize((256, 256))  # Assuming model expects this size
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        prediction = disease_model.predict(img_array)
        return str(np.argmax(prediction))
    return render_template('predict_disease.html')

@app.route('/recommend_crop', methods=['GET', 'POST'])
def recommend_crop():
    if request.method == 'POST':
        soil_type = request.form['soil_type']
        rainfall = float(request.form['rainfall'])
        temperature = float(request.form['temperature'])
        humidity = float(request.form['humidity'])
        
        input_data = pd.DataFrame([[soil_type, rainfall, temperature, humidity]], columns=['soil_type', 'rainfall', 'temperature', 'humidity'])
        prediction = recommendation_model.predict(input_data)
        return str(prediction[0])
    return render_template('recommend_crop.html')

@app.route('/place_order', methods=['GET', 'POST'])
def place_order():
    if request.method == 'POST':
        product_id = int(request.form['product_id'])
        consumer_id = session['id']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO orders VALUES (NULL, %s, %s)', (product_id, consumer_id,))
        mysql.connection.commit()
        return 'Order placed successfully!'
    return render_template('place_order.html')

if __name__ == '__main__':
    app.run(debug=True)
