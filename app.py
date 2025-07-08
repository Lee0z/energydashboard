from flask import Flask, jsonify, render_template, request, redirect, url_for
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
    name = db.Column(db.String(50), unique=True, nullable=False)  # Add unique=True
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
    tapo_ip = os.getenv('TAPO_IP')
    if tapo_ip:
        # Check if the device already exists by name or IP
        existing_device = TapoDevice.query.filter(
            (TapoDevice.ip_address == tapo_ip) | (TapoDevice.name == "PC_RIG")
        ).first()
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
    sort_by = request.args.get('sort_by', 'timestamp')
    order = request.args.get('order', 'asc')
    filter_device_id = request.args.get('device_id', None)

    query = EnergyData.query
    if filter_device_id:
        query = query.filter_by(device_id=filter_device_id)
    
    if order == 'desc':
        query = query.order_by(db.desc(getattr(EnergyData, sort_by)))
    else:
        query = query.order_by(getattr(EnergyData, sort_by))

    energy_data = query.all()
    return render_template('tapo_devices_energy_history.html', energy_data=energy_data, sort_by=sort_by, order=order, filter_device_id=filter_device_id)

@app.route('/solar_data_history', methods=['GET'])
def solar_data_history():
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'asc')
    filter_source = request.args.get('source', None)

    query = SolarPowerData.query
    if filter_source:
        query = query.filter_by(source=filter_source)
    
    if order == 'desc':
        query = query.order_by(db.desc(getattr(SolarPowerData, sort_by)))
    else:
        query = query.order_by(getattr(SolarPowerData, sort_by))

    solar_data = query.all()
    return render_template('solar_data_history.html', solar_data=solar_data, sort_by=sort_by, order=order, filter_source=filter_source)

@app.route('/add_tapo_device', methods=['GET', 'POST'])
def add_tapo_device():
    if request.method == 'POST':
        name = request.form['name']
        ip_address = request.form['ip_address']
        # Check if the device already exists
        existing_device = TapoDevice.query.filter_by(ip_address=ip_address).first()
        if not existing_device:
            # Add the new Tapo device
            new_device = TapoDevice(name=name, ip_address=ip_address)
            db.session.add(new_device)
            db.session.commit()
            return redirect(url_for('tapo_devices_energy_history'))
        else:
            return render_template('add_tapo_device.html', error="Device with this IP address already exists.")
    return render_template('add_tapo_device.html')

def fetch_solar_data():
    try:
        response = requests.get("http://localhost:5000/solar")
        response.raise_for_status()
        data = response.json()
        for entry in data:
            solar_data = SolarPowerData(
                date=datetime.strptime(entry['date'], '%Y-%m-%d'),
                power=entry['power'],
                source=entry['source']
            )
            db.session.add(solar_data)
        db.session.commit()
    except Exception as e:
        print(f"Error fetching solar data: {e}")

def fetch_energy_data():
    try:
        response = requests.get("http://localhost:5000/energy")
        response.raise_for_status()
        data = response.json()
        for entry in data:
            energy_data = EnergyData(
                timestamp=datetime.strptime(entry['timestamp'], '%Y-%m-%dT%H:%M:%S'),
                device_id=entry['device_id'],
                energy_consumed=entry['energy_consumed']
            )
            db.session.add(energy_data)
        db.session.commit()
    except Exception as e:
        print(f"Error fetching energy data: {e}")

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_solar_data, 'interval', seconds=10, id='fetch_solar_data')
    scheduler.add_job(fetch_energy_data, 'interval', seconds=10, id='fetch_energy_data')
    scheduler.start()
    app.run(port=5003, use_reloader=False)

