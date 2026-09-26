"""Integration & Health Check API Test script for CI."""

import urllib.request
import json
import sys

def main():
    print("Testing /health endpoint...")
    url = "http://127.0.0.1:8000/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Health response:", data)
            # Response is wrapped in BaseResponse: {"success": true, "data": {"status": "ok"}}
            if data.get("success") is True or data.get("data", {}).get("status") == "ok":
                print("API Health check passed!")
                return 0
    except Exception as e:
        print(f"API Health check failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
