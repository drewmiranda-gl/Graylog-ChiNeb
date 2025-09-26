import requests
import json
import time
import sys

# --- Configuration ---
# Replace with your Graylog cloud account domain (without http:// or https://)
GRAYLOG_DOMAIN = "yourdomain.graylog.cloud" 
# Replace with the specific Adapter ID you are targeting
ADAPTER_ID = "Adapter_ID"
# IMPORTANT: Replace with your actual Graylog API token.
# Keep this token secure and do not expose it publicly.
API_TOKEN = "Your_API_Token"


def upload_data_to_graylog(data_payload):
    """
    Sends a data payload to the specified Graylog MongoDB lookup adapter,
    processing each entry individually.

    Args:
        data_payload (list): A list of dictionaries containing the data to upload.
    """
    if API_TOKEN == "YOUR_GRAYLOG_API_TOKEN":
        print("ERROR: Please replace 'YOUR_GRAYLOG_API_TOKEN' with your actual API token.")
        return

    # Construct the full API endpoint URL
    # Use http:// because your domain includes port 9000, which is typically for non-HTTPS traffic.
    url = f"http://{GRAYLOG_DOMAIN}/api/plugins/org.graylog.plugins.lookup/lookup/adapters/mongodb/{ADAPTER_ID}"

    # Set the necessary headers for the request
    headers = {
        "Content-Type": "application/json",
        "X-Requested-By": "Python Script"  # Recommended header to identify the client
    }

    print(f"Sending data to: {url}")
    print(f"Preparing to send {len(data_payload)} entries to Graylog one by one.")

    # Iterate through the list of data and send each item in a separate request
    for i, item in enumerate(data_payload):
        # Use a key from your data for the lookup. 'sAMAccountName' is a good candidate.
        key = item.get("sAMAccountName")
        if not key:
            print(f"\n[{i+1}/{len(data_payload)}] ⏩ SKIPPING: Item has no 'sAMAccountName'.")
            continue

        # The API requires a single object with 'key', 'values', and 'data_adapter_id'.
        # Based on the schema, 'values' is an array of strings. We will serialize
        # the user data object into a JSON string and place it in the array.
        api_entry_payload = {
            "key": str(key),
            "values": [json.dumps(item)],
            "data_adapter_id": ADAPTER_ID
        }
        
        print(f"\n[{i+1}/{len(data_payload)}] 📤 SENDING: key='{key}'")

        try:
            # Send the POST request with the JSON data for a single entry
            response = requests.post(
                url, 
                headers=headers, 
                auth=(API_TOKEN, 'token'), 
                data=json.dumps(api_entry_payload), 
                timeout=15
            )

            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()

            # Check for success status codes
            if response.status_code in [200, 201, 202, 204]:
                print(f"[{i+1}/{len(data_payload)}] ✅ SUCCESS: Entry for key='{key}' sent.")
            else:
                print(f"[{i+1}/{len(data_payload)}] ⚠️ WARNING: Unexpected status code {response.status_code} for key='{key}'.")
                print(f"Response content: {response.text}")

        except requests.exceptions.HTTPError as http_err:
            print(f"[{i+1}/{len(data_payload)}] ❌ FAILED: HTTP Error for key='{key}': {http_err}")
            print(f"Response Body: {response.text}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"[{i+1}/{len(data_payload)}] ❌ FAILED: Connection Error for key='{key}': {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"[{i+1}/{len(data_payload)}] ❌ FAILED: Timeout Error for key='{key}': {timeout_err}")
        except requests.exceptions.RequestException as err:
            print(f"[{i+1}/{len(data_payload)}] ❌ FAILED: An unexpected error occurred for key='{key}': {err}")
        
        # Optional: Add a small delay to avoid rate-limiting
        time.sleep(0.1)


def load_data_from_file(filename="ad_users.json"):
    """
    Loads a list of user data from a specified JSON file.
    
    Args:
        filename (str): The name of the JSON file to read.
        
    Returns:
        list: A list of dictionaries loaded from the file, or None if an error occurs.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            print(f"Successfully opened and reading '{filename}'...")
            data = json.load(f)
            if not isinstance(data, list):
                print(f"❌ ERROR: The JSON in '{filename}' is not a list. It should start with '[' and end with ']'.")
                return None
            return data
    except FileNotFoundError:
        print(f"❌ ERROR: The file '{filename}' was not found in the same directory as the script.")
        return None
    except json.JSONDecodeError:
        print(f"❌ ERROR: The file '{filename}' contains invalid JSON. Please check its format.")
        return None
    except Exception as e:
        print(f"❌ ERROR: An unexpected error occurred while reading the file: {e}")
        return None


if __name__ == "__main__":
    # Load the data from the ad_users.json file
    json_to_upload = load_data_from_file("ad_users.json")

    # If the file was loaded successfully, proceed to upload the data
    if json_to_upload:
        upload_data_to_graylog(json_to_upload)
    else:
        print("\nScript finished with errors. No data was sent to Graylog.")
        sys.exit(1) # Exit with a non-zero status code to indicate failure

