from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from config import app, db, csrf
from models import User, UserHistory
from datetime import datetime
import numpy as np
import pandas as pd
import os
import pickle
import bz2
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from sqlalchemy.exc import IntegrityError
import random
import math
import io

# Load the model and label encoder
def load_model():
    file_path = os.path.join(os.path.dirname(__file__), 'random_forest_model.pbz2')
    with bz2.BZ2File(file_path, 'rb') as model_file:
        return pickle.load(model_file)

def load_label_encoder():
    file_path = os.path.join(os.path.dirname(__file__), 'label_encoder.pkl')
    with open(file_path, 'rb') as model_file:
        return pickle.load(model_file)

model = load_model()
label_encoder = load_label_encoder()

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8),
        EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')

class InputForm(FlaskForm):
    n_value = FloatField('N (kg/ha)', validators=[DataRequired(), NumberRange(min=0)])
    p_value = FloatField('P (kg/ha)', validators=[DataRequired(), NumberRange(min=0)])
    k_value = FloatField('K (kg/ha)', validators=[DataRequired(), NumberRange(min=0)])
    ph_values = FloatField('PH', validators=[DataRequired(), NumberRange(min=1, max=14)])
    humidity = FloatField('Humidity (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    temperature = FloatField('Temperature (C°)', validators=[DataRequired(), NumberRange(min=0, max=65)])
    rainfall = FloatField('Rainfall (mm/year)', validators=[DataRequired(), NumberRange(min=0)])

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html', form=form)

def is_strong_password(password):
    return len(password) >= 8

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if not is_strong_password(password):
            flash('Password is weak. It must be at least 8 characters long.', 'danger')
        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists', 'danger')
            else:
                hashed_password = generate_password_hash(password)
                new_account = User(username=username, password=hashed_password)
                try:
                    db.session.add(new_account)
                    db.session.commit()
                    flash('Signup successful! You can now log in.', 'success')
                    return render_template('signup_success.html', username=username)
                except IntegrityError:
                    db.session.rollback()
                    flash('An error occurred. Please try again.', 'danger')

    return render_template('signup.html', form=form)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if not user:
            return redirect(url_for('login'))

        form = InputForm()
        if form.validate_on_submit():
            try:
                N = form.n_value.data
                P = form.p_value.data
                K = form.k_value.data
                PH = form.ph_values.data
                Humidity = form.humidity.data
                Temp = form.temperature.data
                rainfall = form.rainfall.data
            except ValueError:
                flash('Invalid input values', 'danger')
                return redirect(url_for('dashboard'))

            values_list = [[N, P, K, Humidity, Temp, PH, rainfall]]
            values_array = np.array(values_list, dtype=float)
            pred = model.predict(values_array)
            prediction = label_encoder.inverse_transform(pred)[0]

            history_entry = UserHistory(
                user_id=user.id,
                n_value=N,
                p_value=P,
                k_value=K,
                ph_values=PH,
                humidity=Humidity,
                temperature=Temp,
                rainfall=rainfall,
                prediction=prediction,
                timestamp=datetime.now()
            )
            try:
                db.session.add(history_entry)
                db.session.commit()
                flash('Prediction successful!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error occurred: ' + str(e), 'danger')

            return redirect(url_for("dashboard", prediction=prediction))

        prediction = request.args.get('prediction')
        return render_template("dashboard.html", form=form, username=session['username'], prediction=prediction, history=user.history)
    else:
        return redirect(url_for('login'))

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/quicktry', methods=['GET', 'POST'])
def quicktry():
    form = InputForm()
    if form.validate_on_submit():
        try:
            N = form.n_value.data
            P = form.p_value.data
            K = form.k_value.data
            PH = form.ph_values.data
            Humidity = form.humidity.data
            Temp = form.temperature.data
            rainfall = form.rainfall.data
        except ValueError:
            flash('Invalid input values', 'danger')
            return redirect(url_for('quicktry'))

        values_list = [[N, P, K, Humidity, Temp, PH, rainfall]]
        values_array = np.array(values_list, dtype=float)
        pred = model.predict(values_array)
        prediction = label_encoder.inverse_transform(pred)[0]

        return render_template("quicktry.html", form=form, prediction=prediction, scroll_to_img=True)

    return render_template("quicktry.html", form=form, prediction=None, scroll_to_img=False)

sensor_data_storage = []

# Define the path to the Excel file
excel_file_path = 'sensor_data.xlsx'

# Create a new Excel file with proper columns if it doesn't exist
if not os.path.exists(excel_file_path):
    df = pd.DataFrame(columns=[
        'N', 'P', 'K', 'Humidity', 'Temperature', 'Soil pH', 'Rainfall', 'Prediction',
        'MQ135', 'MQ7', 'MQ9', 'MQ8', 'MQ3', 'MQ5', 'Soil Moisture', 'Water pH'
    ])
    df.to_excel(excel_file_path, index=False)

@app.route('/sensor-data', methods=['POST'])
@csrf.exempt
def sensor_data():
    data = request.form

    def get_value(key, default=0.0):
        value = data.get(key, default)
        try:
            value = float(value)
            if math.isnan(value):
                value = 0.0
        except (ValueError, TypeError):
            value = 0.0
        return value

    # Function to calibrate soil moisture
    def calibrate_soil_moisture(raw_value):
        calibrated_value = max(0, min(100, 100 - (raw_value / 4096) * 100))
        return calibrated_value*100

    sensor_data = {
        'humidity': get_value('humidity'),
        'temperature': get_value('temperature'),
        'soil_moisture': calibrate_soil_moisture(get_value('soilMoisture')),
        'rainfall': get_value('rainfall'),
        'water_ph': get_value('water_ph'),
        'mq135': get_value('MQ135'),
        'mq7': get_value('MQ7'),
        'mq9': get_value('MQ9'),
        'mq8': get_value('MQ8'),
        'mq5': get_value('MQ5'),
        'mq3': get_value('MQ3')
    }

    # Generate random NPK values and soil pH
    N = random.randint(15, 250)
    P = random.randint(15, 250)
    K = random.randint(15, 250)
    PH = random.uniform(0, 14)
    sensor_data['soil_ph'] = PH
    rainfall = 500
    values_list = [[N, P, K, sensor_data['humidity'], sensor_data['temperature'], PH, rainfall]]
    values_array = np.array(values_list, dtype=float)
    pred = model.predict(values_array)
    prediction = label_encoder.inverse_transform(pred)[0]

    # Append the prediction to sensor data
    sensor_data['prediction'] = prediction

    # Append the new row to the sensor_data_storage
    sensor_data_storage.append(sensor_data)

    # Save to Excel file
    df = pd.DataFrame(sensor_data_storage)
    df.to_excel(excel_file_path, index=False)

    return jsonify({'status': 'success', 'message': 'Data received successfully', 'data': sensor_data}), 200

@app.route('/get-sensor-data', methods=['GET'])
def get_sensor_data():
    if sensor_data_storage:
        return jsonify(sensor_data_storage[-1])
    else:
        return jsonify({})

@app.route('/download_excel')
def download_excel():
    df = pd.DataFrame(sensor_data_storage)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='SensorData')
    writer.save()
    output.seek(0)

    return send_file(output, as_attachment=True, download_name='sensor_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/display-sensor-data')
def display_sensor_data():
    return render_template('sensor_data.html', sensor_data=sensor_data_storage)

if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, host='0.0.0.0', port=5000)
