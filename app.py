from flask import Flask, jsonify, render_template
import asyncio
import energyCheck as ec
import scraperOmnik
import scraperZeverSolar

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/energy', methods=['GET'])
def get_energy():
    try:
        result = asyncio.run(ec.get_current_power())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/solar', methods=['GET'])
def get_solar():
    try:
        # Fetch data from Omnik
        omnik_data = scraperOmnik.scrapeOmnik()
        
        # Fetch data from ZeverSolar
        zeversolar_data = scraperZeverSolar.scrapeZeverSolar()
        
        # Combine the data
        combined_data = {
            "omnik": omnik_data,
            "zeversolar": zeversolar_data
        }

        return jsonify(combined_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/energy_page', methods=['GET'])
def energy_page():
    return render_template('energy.html')

@app.route('/solar_page', methods=['GET'])
def solar_page():
    return render_template('solar.html')

if __name__ == '__main__':
    app.run(port=5000)
