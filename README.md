# Energy Dashboard

A very *simple* dashboard for TAPO P110 and Omnik / Zeversolar solar inverters I use.

Big thanks to https://github.com/mihai-dinculescu/tapo for the TAPO API client.

## Project setup
1. Requirements:
   - Python3
   - Docker
     
2. Installation:
    ```
     pip install -r requirements.txt
     docker-compose up --build
     ```

## Important

The project is not intended to use on production environment since Flask is not secure.

## Docker Configuration

The application is configured to run in Docker and is accessible via localhost:5003. The Flask app runs inside the container and exposes port 5003.

### Running the Application
```bash
docker-compose up --build
```

The application will be available at: http://127.0.0.1:5003

### Environment Setup
Create a `.env` file with your device configuration:
```bash
cp .env.example .env
# Edit .env with your device IP addresses and credentials
```

## Local development
After setting up container, Flask app should start by itself.

In order to rerun flask app use command:
 ```python3 app.py```
