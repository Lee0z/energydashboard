import requests
from requests.auth import HTTPBasicAuth
import re
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def scrapeOmnik():
    base_url = os.getenv('OMNIK_URL')
    status_url = f"{base_url}/status.html"
    js_url = f"{base_url}/js/status.js"
    username = os.getenv('OMNIK_USERNAME')
    password = os.getenv('OMNIK_PASSWORD')

    try:
        # Perform login
        session = requests.Session()
        login_response = session.get(base_url, auth=HTTPBasicAuth(username, password))
        login_response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        
        # Access the status page using the same session
        status_response = session.get(status_url, auth=HTTPBasicAuth(username, password))
        status_response.raise_for_status()
        
        # Fetch the status.js file
        js_response = session.get(js_url, auth=HTTPBasicAuth(username, password))
        js_response.raise_for_status()
        
        # Extract the webData variable from the JavaScript code
        js_content = js_response.text
        match = re.search(r'var webData="([^"]+)"', js_content)
        if match:
            web_data = match.group(1)
            # Split the webData string into individual data points
            data_points = web_data.split(',')
            current_power = data_points[5] + " W" if data_points[5] else None
            yield_today = str(float(data_points[6]) / 100) + " kWh" if data_points[6] else None
            yield_total = str(float(data_points[7]) / 10) + " kWh" if data_points[7] else None

            if current_power and yield_today and yield_total:
                data = {
                    "current_power": current_power,
                    "yield_today": yield_today,
                    "yield_total": yield_total,
                    "datetime": datetime.utcnow().isoformat()  # Include the current date and time
                }
                return {"data": data}
            else:
                return {"error": "Required data elements not found in the webData variable"}
        else:
            return {"error": "webData variable not found in the JavaScript code"}
    
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}
    except requests.exceptions.ConnectionError as conn_err:
        return {"error": f"Connection error occurred: {conn_err}"}
    except requests.exceptions.Timeout as timeout_err:
        return {"error": f"Timeout error occurred: {timeout_err}"}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"An error occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

# Example usage
if __name__ == "__main__":
    result = scrapeOmnik()
    print(result)