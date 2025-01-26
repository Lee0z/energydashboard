import asyncio
import os
from tapo import ApiClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def get_current_power(db, TapoDevice, EnergyData):
    try:
        tapo_username = os.getenv('TAPO_USERNAME')
        tapo_password = os.getenv('TAPO_PASSWORD')
        tapo_ip = os.getenv('TAPO_IP')

        if not tapo_username or not tapo_password or not tapo_ip:
            raise ValueError("Environment variables TAPO_USERNAME, TAPO_PASSWORD, and TAPO_IP must be set")

        client = ApiClient(tapo_username, tapo_password)
        device = await client.p110(tapo_ip)

        current_power = await device.get_current_power()
        
        # Find or create the TapoDevice by IP address
        tapo_device = TapoDevice.query.filter_by(ip_address=tapo_ip).first()
        if not tapo_device:
            tapo_device = TapoDevice(name="Tapo Device", ip_address=tapo_ip)
            db.session.add(tapo_device)
            db.session.commit()

        # Store energy data in the database
        energy_data = EnergyData(
            device_id=tapo_device.id,
            timestamp=datetime.utcnow(),
            power=current_power.current_power  # Access the attribute directly
        )
        db.session.add(energy_data)
        db.session.commit()

        return {
            "current_power": current_power.current_power  # Return current power for real-time tracking
        }
    
    except Exception as e:
        return {"error": str(e)}

async def main(db, TapoDevice, EnergyData):
    result = await get_current_power(db, TapoDevice, EnergyData)
    print(result)

if __name__ == "__main__":
    from app import db, TapoDevice, EnergyData
    asyncio.run(main(db, TapoDevice, EnergyData))
