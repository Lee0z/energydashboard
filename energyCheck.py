import asyncio
import os
from tapo import ApiClient
from dotenv import load_dotenv

load_dotenv()

async def get_current_power():
    try:
        tapo_username = os.getenv('TAPO_USERNAME')
        tapo_password = os.getenv('TAPO_PASSWORD')
        tapo_ip = os.getenv('TAPO_IP')

        if not tapo_username or not tapo_password or not tapo_ip:
            raise ValueError("Environment variables TAPO_USERNAME, TAPO_PASSWORD, and TAPO_IP must be set")

        client = ApiClient(tapo_username, tapo_password)
        device = await client.p110(tapo_ip)

        current_power = await device.get_current_power()
        return current_power.to_dict()
    
    except Exception as e:
        return {"error": str(e)}

async def main():
    result = await get_current_power()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
