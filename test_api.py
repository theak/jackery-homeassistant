#!/usr/bin/env python3
"""Test script for Jackery API debugging."""

import logging
import sys

from api import JackeryAPI, JackeryAuthenticationError

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_jackery_api(username, password):
    """Test the Jackery API connection."""
    print(f"Testing Jackery API with username: {username}")

    try:
        # Create API instance
        api = JackeryAPI(account=username, password=password)

        # Test login
        print("Testing login...")
        if api.login():
            print("✅ Login successful!")
        else:
            print("❌ Login failed!")
            return False

        # Test device list
        print("Testing device list...")
        device_list = api.get_device_list()
        devices = device_list.get("data", [])
        print(f"✅ Found {len(devices)} devices")

        for device in devices:
            device_id = device.get("devId")
            device_name = device.get("devName", "Unknown")
            print(f"  - Device: {device_name} (ID: {device_id})")

        # Test device detail for first device
        if devices:
            first_device = devices[0]
            device_id = first_device["devId"]
            print(f"Testing device detail for {device_id}...")

            device_detail = api.get_device_detail(device_id)
            properties = device_detail.get("data", {}).get("properties", {})
            print(f"✅ Device detail retrieved with {len(properties)} properties")

            for key, value in properties.items():
                print(f"  - {key}: {value}")

        return True

    except JackeryAuthenticationError as e:
        print(f"❌ Authentication error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_api.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    success = test_jackery_api(username, password)
    sys.exit(0 if success else 1)
