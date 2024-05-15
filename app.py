from flask import Flask, jsonify
from flask import request
import threading
from azure.iot.hub import IoTHubRegistryManager, DigitalTwinClient
import logging
import asyncio
from azure.eventhub.aio import EventHubConsumerClient
import msrest
import json

app = Flask(__name__)

#connection string for sending C2D messages
connection_str = "HostName=rd-iothub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=TcpaortpcdjcMkZDre1kVhBMdkAZVUXYPAIoTPaN/kQ="
device_id = "TND_WH_10521C663374"

@app.route('/')
def index():
    return jsonify({'message': 'Welcome to the IoT HUB sample API'})

@app.route('/up', methods=['POST'])
def up():
    # Extract the value from the POST request body
    data = request.json
    value = data.get('value', None)  # Assuming the value is sent as a JSON object with a key 'value'

    if value is None:
        return jsonify({'error': 'Value not provided'}), 400

    data = {
    "TRANSMISSION_PATH": {
        "TX": "BACKEND",
        "RX": "DEVICE",
        "BACKEND_DATA": {
            "APP_STATE": "OPEN",
            "AVERAGE_POWER_WATT": "NEED",
            "ACTIVATION": "DONE",
            "WIFI_SETTING": "KEEP",
            "APP_DATA": {
                "MODE_DATA": {
                    "FEATURES": "SLEEP",
                    "MODE": "OFF"
                },
                "COMPONENT_DATA": {
                    "PLASMA": "OFF",
                    "FAN": "OFF",
                    "H_LOUVRE": "POS_1",
                    "V_LOUVRE": "POS_1"
                },
                "CONTROL_DATA": {
                    "TIMER_STATE": "OFF",
                    "TIMER_HOURS": "0",
                    "TEMP_CELSIUS_USER": value
                }
            }
        }
    }
}
    
    sent_message = json.dumps(data)

    try:
        registry_manager = IoTHubRegistryManager.from_connection_string(connection_str)
        registry_manager.send_c2d_message(device_id, sent_message)
        print(sent_message)
        return jsonify({'message': f"Message {sent_message} sent successfully"})
    except msrest.exceptions.HttpOperationError as ex:
        return jsonify({'error': f"HttpOperationError: {ex.response.text}"})
    except Exception as ex:
        return jsonify({'error': f"Unexpected error: {ex}"})

@app.route('/down', methods=['POST'])
def down():
    # Extract the value from the POST request body
    data = request.json
    value = data.get('value', None)  # Assuming the value is sent as a JSON object with a key 'value'

    
    if value is None:
        return jsonify({'error': 'Value not provided'}), 400
    
    data = {
    "TRANSMISSION_PATH": {
        "TX": "BACKEND",
        "RX": "DEVICE",
        "BACKEND_DATA": {
            "APP_STATE": "OPEN",
            "AVERAGE_POWER_WATT": "NEED",
            "ACTIVATION": "DONE",
            "WIFI_SETTING": "KEEP",
            "APP_DATA": {
                "MODE_DATA": {
                    "FEATURES": "SLEEP",
                    "MODE": "OFF"
                },
                "COMPONENT_DATA": {
                    "PLASMA": "OFF",
                    "FAN": "OFF",
                    "H_LOUVRE": "POS_1",
                    "V_LOUVRE": "POS_1"
                },
                "CONTROL_DATA": {
                    "TIMER_STATE": "OFF",
                    "TIMER_HOURS": "0",
                    "TEMP_CELSIUS_USER": value
                }
            }
        }
    }
}
    sent_message = json.dumps(data)
    try:
        registry_manager = IoTHubRegistryManager.from_connection_string(connection_str)
        registry_manager.send_c2d_message(device_id, sent_message)
        return jsonify({'message': f"Message {sent_message} sent successfully"})
    except msrest.exceptions.HttpOperationError as ex:
        return jsonify({'error': f"HttpOperationError: {ex.response.text}"})
    except Exception as ex:
        return jsonify({'error': f"Unexpected error: {ex}"})

connection_str_event_hub = 'Endpoint=sb://iothub-ns-rd-iothub-57224525-ae5daa8d09.servicebus.windows.net/;SharedAccessKeyName=iothubowner;SharedAccessKey=TcpaortpcdjcMkZDre1kVhBMdkAZVUXYPAIoTPaN/kQ=;EntityPath=rd-iothub'
consumer_group = '$Default'
eventhub_name = 'rd-iothub'
client = EventHubConsumerClient.from_connection_string(connection_str_event_hub, consumer_group, eventhub_name=eventhub_name)

logger = logging.getLogger("azure.eventhub")
logging.basicConfig(level=logging.INFO)

DataJSON = ""

@app.route('/get_data')
def get_display_value():
    if DataJSON == "":
        return jsonify({'response': "no data available"})
    return extract_data_from_event(DataJSON.body_as_str())


# Function to extract and format the required data
def extract_data_from_event(json_data):
    # Parse the JSON string
    parsed_data = json.loads(json_data)
    print(parsed_data)

    # Extract the desired fields
    component_data = parsed_data['PRODUCT_DATA']['DEVICE_DATA']['COMPONENT_DATA']
    timer_data = parsed_data['PRODUCT_DATA']['DEVICE_DATA']['TIMER_DATA']
    temp_data = parsed_data['PRODUCT_DATA']['DEVICE_DATA']['TEMP_DATA']
    fault_data = parsed_data['PRODUCT_DATA']['DEVICE_DATA']['FAULT_DATA']
    humidity_data = parsed_data['PRODUCT_DATA']['DEVICE_DATA']['HUMIDITY_DATA']
    power_data = parsed_data['PRODUCT_DATA']['DEVICE_DATA']['POWER_DATA']

    # Create a new JSON object with the extracted data
    response_json = {
        "component_data": component_data,
        "timer_data": timer_data,
        "temp_data": temp_data,
        "fault_data": fault_data,
        "humidity_data": humidity_data,
        "power_data": power_data
    }

    return response_json

async def on_event(partition_context, event):
    logger.info("Received event from partition {}".format(partition_context.partition_id))
    global DataJSON
    DataJSON = event.body_as_str()
    print(DataJSON)
    await partition_context.update_checkpoint(event)

client = EventHubConsumerClient.from_connection_string(connection_str_event_hub, consumer_group, eventhub_name=eventhub_name)

async def receive():
    async with client:
        await client.receive(
            on_event=on_event,
            starting_position="-1",  # "-1" is from the beginning of the partition.
        )
        # receive events from specified partition:
        # await client.receive(on_event=on_event, partition_id='0')

def run_flask():
    app.run(debug=True)

if __name__ == '__main__':
    # Start the Event Hub receiver thread
    event_hub_thread = threading.Thread(target=asyncio.run, args=(receive(),))
    event_hub_thread.start()

    # Start the Flask server in the main thread
    run_flask()