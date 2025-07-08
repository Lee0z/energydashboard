import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def scrapeZeverSolar():
    base_url = os.getenv('ZEVERSOLAR_URL')
    data_url = f"{base_url}/home.cgi"

    try:
        # Fetch the data from home.cgi with a timeout
        response = requests.get(data_url, timeout=5)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        
        # Parse the response data
        data = response.text
        parsed = data.split("\n")
        
        # Extract the required information
        row_count = int(parsed[8])
        for i in range(row_count):
            base_index = 9 + i * 4
            pac = parsed[base_index + 1]
            e_today = parsed[base_index + 2]
            status = parsed[base_index + 3]
            if status.startswith("OK"):
                break
        
        # Create a dictionary with the extracted data
        data_dict = {
            "current_power": pac + " W",
            "yield_today": e_today + " kWh",
            "datetime": datetime.utcnow().isoformat()  # Include the current date and time
        }
        
        # Return the data as a dictionary
        return {"data": data_dict}
    
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}
    except requests.exceptions.ConnectionError as conn_err:
        return {"error": "ZeverSolar is offline"}
    except requests.exceptions.Timeout as timeout_err:
        return {"error": "ZeverSolar is offline"}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"An error occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

# Example usage
if __name__ == "__main__":
    result = scrapeZeverSolar()
    print(result)