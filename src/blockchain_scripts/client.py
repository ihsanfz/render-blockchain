import asyncio
import aioipfs
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import httpx
import requests

# Connect to the blockchain (e.g., Polygon)
POLYGON_RPC_URL = ""  # Replace with your RPC URL
web3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))

# Inject PoA middleware
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# Verify the connection
if web3.is_connected():
    print("Connected to the blockchain!")
else:
    print("Failed to connect to the blockchain.")

# Smart contract details (replace with your deployed contract address and ABI)
CONTRACT_ADDRESS = ""
with open(r'contract_abi.json', 'r') as file:
    CONTRACT_ABI = file.read()  # Replace with your contract's ABI

# Load the contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Your wallet address and private key (for signing transactions)
WALLET_ADDRESS = ""
PRIVATE_KEY = ""

async def upload_file_to_ipfs(file_path):
    # Connect to the local IPFS node
    client = aioipfs.AsyncIPFS(host='127.0.0.1', port=5001) #Connect to IPFS hosted on client

    # Initialize CID to None
    cid = None

    # Upload the file to IPFS
    async for added_file in client.add(file_path):
        cid = added_file['Hash']
        print(f"File uploaded to IPFS. CID: {cid}")

    # Close the IPFS client connection
    await client.close()

    # Check if CID was assigned
    if cid is None:
        raise Exception("Failed to upload file to IPFS: No CID returned.")

    return cid

async def store_metadata_on_blockchain(cid, client_info):
    # Create the transaction
    transaction = contract.functions.storeFile(cid, client_info).build_transaction({
        'from': WALLET_ADDRESS,
        'gas': 2000000,
        'nonce': web3.eth.get_transaction_count(WALLET_ADDRESS),
    })

    # Sign the transaction
    signed_txn = web3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)

    # Send the transaction
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"File metadata stored on blockchain. Transaction hash: {tx_hash.hex()}")

async def send_cid_to_host(cid, host_url):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            # Send the CID to the host
            response = requests.post('http://<host_ip>:5000/receive_file', json={'cid': cid})
            if response.status_code == 200:
                print("CID sent successfully. Waiting for rendered image...")

                # Save the rendered image
                with open('rendered_image.png', 'wb') as img_file:
                    img_file.write(response.content)
                print("Rendered image received and saved as 'rendered_image.png'.")
            else:
                print(f"Failed to send CID. Status code: {response.status_code}")
                print(f"Response content: {response.text}")  # Debugging: Print the response content
        except Exception as e:
            print(f"An error occurred while sending CID: {e}")

async def main():
    blender_file_path = "stuff.blend"  # Path to the Blender file
    host_url = "http://<host_ip>:5000"  # Host server URL
    client_info = "Client1"  # Replace with client info

    # Upload the file to IPFS and get the CID
    cid = await upload_file_to_ipfs(blender_file_path)

    # Store the CID and metadata on the blockchain
    await store_metadata_on_blockchain(cid, client_info)

    # Send the CID to the host
    await send_cid_to_host(cid, host_url)

if __name__ == "__main__":
    asyncio.run(main())
