from flask import Flask, request, send_file
import subprocess
import os
import aioipfs
import asyncio
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Connect to the blockchain (e.g., Polygon)
POLYGON_RPC_URL = ""  # Replace with your RPC URL
web3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))

# Inject PoA middleware
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# Verify the connection
if web3.is_connected():
    logger.info("Connected to the blockchain!")
else:
    logger.error("Failed to connect to the blockchain.")

# Smart contract details (replace with your deployed contract address and ABI)
CONTRACT_ADDRESS = ""
with open(r'.\contract_abi.json', 'r') as file:
    CONTRACT_ABI = file.read()  # Replace with your contract's ABI

# Load the contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Render the Blender file (synchronous)
def render_blender_file(file_path):
    # Ensure the output directory is the same as the script's directory
    script_directory = os.path.dirname(os.path.abspath(__file__))
    output_image = os.path.join(script_directory, "output.png")

    # Blender command to render the file
    blender_command = [
        "blender",  # Path to Blender executable
        "-b", file_path,  # Run in background mode
        "-o", output_image,  # Output image path (without frame number)
        "-F", "PNG",  # Output format
        "-x", "1",  # Overwrite existing files
        "-f", "1",  # Render frame 1
    ]
    subprocess.run(blender_command)

    # Blender appends a frame number to the output file, so we need to rename it
    rendered_file = f"{output_image}0001.png"
    if os.path.exists(rendered_file):
        os.rename(rendered_file, output_image)

    return output_image

# Asynchronous function to retrieve a file from IPFS
async def retrieve_file_from_ipfs(cid):
    # Connect to the client's IPFS node
    client = aioipfs.AsyncIPFS(host='<client_ip>', port=5001)  # Replace with client's IP

    try:
        # Retrieve the file from IPFS
        file_data = await client.cat(cid)
        return file_data
    finally:
        # Close the IPFS client connection
        await client.close()

@app.route('/receive_file', methods=['POST'])
def receive_file():
    try:
        logger.debug("Received request to /receive_file")

        if 'cid' not in request.json:
            logger.error("No CID provided in the request")
            return "No CID provided", 400

        cid = request.json['cid']
        logger.debug(f"CID received: {cid}")

        # Validate the CID
        if not cid or not isinstance(cid, str):
            logger.error(f"Invalid CID provided: {cid}")
            return "Invalid CID provided.", 400

        # Verify the CID against the blockchain
        logger.debug("Verifying CID against the blockchain...")
        stored_cid, client_info, timestamp = contract.functions.getFile(cid).call()
        if stored_cid != cid:
            logger.error(f"CID does not match the blockchain record. Stored CID: {stored_cid}, Received CID: {cid}")
            return "CID does not match the blockchain record.", 400

        # Run the async function to retrieve the file
        logger.debug("Retrieving file from IPFS...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        file_data = loop.run_until_complete(retrieve_file_from_ipfs(cid))

        # Save the file locally
        file_path = "received_project.blend"
        with open(file_path, 'wb') as f:
            f.write(file_data)
        logger.debug(f"File saved locally at: {file_path}")

        # Render the Blender file
        logger.debug("Rendering Blender file...")
        output_image = render_blender_file(file_path)

        # Send the rendered image back to the client
        logger.debug("Sending rendered image back to the client...")
        return send_file(output_image, mimetype='image/png')

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return f"An error occurred: {str(e)}", 500

if __name__ == "__main__":
    # Start the Flask server
    app.run(host="0.0.0.0", port=5000)
