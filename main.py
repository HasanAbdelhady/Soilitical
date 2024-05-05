from flask import render_template, request, redirect, url_for, session,flash
from werkzeug.security import check_password_hash, generate_password_hash
from config import app, db
from models import User, UserHistory
from datetime import datetime
import numpy as np
import os
import pickle

#loading the model
def load_model():
    file_path = os.path.join(os.path.dirname(__file__), 'random_forest_model.pkl')
    with open(file_path, 'rb') as model_file:
        return pickle.load(model_file)
    
def label_encoder():
    file_path = os.path.join(os.path.dirname(__file__), 'label_encoder.pkl')
    with open(file_path, 'rb') as model_file:
        return pickle.load(model_file)
model = load_model()
label_encoder = label_encoder()

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  # Initialize error variable

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            # Query the database for the user
            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password, password):
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid username or password'  # Set error message
        except Exception as e:
            # Handle any potential exceptions
            error = 'An error occurred: ' + str(e)

    return render_template('login.html', error=error)
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('signup.html', error='Username already exists')

        if password == confirm_password :
            hashed_password = generate_password_hash(password)

            new_account = User(username=username, password=hashed_password)

            db.session.add(new_account)
            db.session.commit()

            return render_template('signup_success.html', username=username)

        else:
            return render_template('signup.html', error='Passwords do not match')

    return render_template('signup.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if request.method == 'POST':
            N = request.form['n_value']
            P = request.form['p_value']
            K = request.form['k_value']
            PH = request.form['ph_values']
            Humidity = request.form['humidity']
            Temp = request.form['temperature']
            rainfall = request.form['rainfall']

            values_list = [[N, P, K, Humidity, Temp, PH, rainfall]]

            values_array = np.array(values_list, dtype=float)
            pred = model.predict(values_array)
            prediction = label_encoder.inverse_transform(pred)
            # Save user history
            history_entry = UserHistory(
                user_id=user.id,
                n_value=N,
                p_value=P,
                k_value=K,
                ph_values=PH,
                humidity=Humidity,
                temperature=Temp,
                rainfall=rainfall,
                prediction=prediction[0],
                timestamp=datetime.now()
            )
            try:
                db.session.add(history_entry)
                db.session.commit()
            except:
                return 'Error Occurred'
            
            return redirect(url_for("dashboard", username=session['username'], prediction=prediction[0], history=user.history))
        prediction = request.args.get('prediction')
        return render_template("dashboard.html", username=session['username'], prediction=prediction, history=user.history)

    else:
        return redirect(url_for('login'))

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/quicktry', methods=['GET', 'POST'])
def quicktry():
    if request.method == 'POST':
        N = request.form['n_value']
        P = request.form['p_value']
        K = request.form['k_value']
        PH = request.form['ph_values']
        Humidity = request.form['humidity']
        Temp = request.form['temperature']
        rainfall = request.form['rainfall']

        values_list = [[N, P, K, Humidity, Temp, PH, rainfall]]

        values_array = np.array(values_list, dtype=float)
        x = model.predict(values_array)
        prediction = label_encoder.inverse_transform(x)
        return render_template("quicktry.html", prediction=prediction[0] )

    return render_template("quicktry.html")


if __name__ == '__main__':
        with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5000, debug=True)
