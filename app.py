from flask import Flask, jsonify, render_template
import asyncio
import energyCheck as ec
import scraperOmnik
import scraperZeverSolar
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class TapoDevice (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)

class SolarData (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    power = db.Column(db.Float, nullable=False)
    yield_today = db.Column(db.Float, nullable=False)
    yield_total = db.Column(db.Float, nullable=True)

class EnergyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('tapo_device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    power = db.Column(db.Float, nullable=False)

class SolarPowerData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    power = db.Column(db.Float, nullable=False)
    yield_today = db.Column(db.Float, nullable=False)
    yield_total = db.Column(db.Float, nullable=True)

@app.before_request
def setup():
    db.create_all()  # Create database tables if they do not exist
    tapo_ip = os.getenv('TAPO_IP')
    if tapo_ip:
        # Check if the device already exists
        existing_device = TapoDevice.query.filter_by(ip_address=tapo_ip).first()
        if not existing_device:
            # Add the Tapo device with the name "PC_RIG"
            new_device = TapoDevice(name="PC_RIG", ip_address=tapo_ip)
            db.session.add(new_device)
            db.session.commit()

def recreate_tables():
    db.drop_all()
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/energy', methods=['GET'])
def get_energy():
    try:
        result = asyncio.run(ec.get_current_power(db, TapoDevice, EnergyData))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/solar', methods=['GET'])
def get_solar():
    combined_data = {}

    try:
        # Fetch data from Omnik
        omnik_data = scraperOmnik.scrapeOmnik()
        if 'error' in omnik_data:
            combined_data['omnik_error'] = omnik_data['error']
        else:
            # Ensure omnik_data is a list of dictionaries
            if isinstance(omnik_data, dict):
                omnik_data = [omnik_data]
            # Store Omnik data in the database
            for data in omnik_data:
                power = float(data['data']['current_power'].replace(' W', ''))  # Strip units and convert to float
                yield_today = float(data['data']['yield_today'].replace(' kWh', ''))  # Strip units and convert to float
                yield_total = float(data['data']['yield_total'].replace(' kWh', '')) if 'yield_total' in data['data'] else None  # Strip units and convert to float
                solar_data = SolarPowerData(
                    source='Omnik',
                    date=datetime.fromisoformat(data['data']['datetime']).date(),  # Use the datetime from the scraper
                    time=datetime.fromisoformat(data['data']['datetime']).time(),  # Use the datetime from the scraper
                    power=power,
                    yield_today=yield_today,
                    yield_total=yield_total
                )
                db.session.add(solar_data)
            combined_data['omnik'] = omnik_data

        # Fetch data from ZeverSolar
        zeversolar_data = scraperZeverSolar.scrapeZeverSolar()
        if 'error' in zeversolar_data:
            combined_data['zeversolar_error'] = zeversolar_data['error']
        else:
            # Ensure zeversolar_data is a list of dictionaries
            if isinstance(zeversolar_data, dict):
                zeversolar_data = [zeversolar_data]
            # Store ZeverSolar data in the database
            for data in zeversolar_data:
                if 'data' in data:
                    power = float(data['data']['current_power'].replace(' W', ''))  # Strip units and convert to float
                    yield_today = float(data['data']['yield_today'].replace(' kWh', ''))  # Strip units and convert to float
                    yield_total = float(data['data']['yield_total'].replace(' kWh', '')) if 'yield_total' in data['data'] else None  # Strip units and convert to float
                    solar_data = SolarPowerData(
                        source='ZeverSolar',
                        date=datetime.fromisoformat(data['data']['datetime']).date(),  # Use the datetime from the scraper
                        time=datetime.fromisoformat(data['data']['datetime']).time(),  # Use the datetime from the scraper
                        power=power,
                        yield_today=yield_today,
                        yield_total=yield_total
                    )
                    db.session.add(solar_data)
            combined_data['zeversolar'] = zeversolar_data

        db.session.commit()

        return jsonify(combined_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/energy_page', methods=['GET'])
def energy_page():
    return render_template('energy.html')

@app.route('/solar_page', methods=['GET'])
def solar_page():
    return render_template('solar.html')

@app.route('/tapo_devices_energy_history', methods=['GET'])
def tapo_devices_energy_history():
    energy_data = EnergyData.query.all()
    return render_template('tapo_devices_energy_history.html', energy_data=energy_data)

@app.route('/solar_data_history', methods=['GET'])
def solar_data_history():
    solar_data = SolarPowerData.query.all()
    return render_template('solar_data_history.html', solar_data=solar_data)

def fetch_solar_data():
    try:
        response = requests.get("http://localhost:5000/solar")
    except Exception as e:
        pass

def fetch_energy_data():
    try:
        response = requests.get("http://localhost:5000/energy")
    except Exception as e:
        pass

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_solar_data, 'interval', seconds=10, id='fetch_solar_data')
    scheduler.add_job(fetch_energy_data, 'interval', seconds=10, id='fetch_energy_data')
    scheduler.start()
    app.run(port=5000, use_reloader=False)