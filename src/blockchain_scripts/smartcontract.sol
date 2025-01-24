// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract IPFSStorage {
    // Struct to store file metadata
    struct File {
        string cid; // IPFS CID
        string client; // Client info
        uint256 timestamp; // Timestamp of upload
    }

    // Mapping to store files by their CID
    mapping(string => File) public files;

    // Event to log file uploads
    event FileUploaded(string cid, string client, uint256 timestamp);

    // Function to store file metadata
    function storeFile(string memory _cid, string memory _client) public {
        require(bytes(_cid).length > 0, "CID cannot be empty");
        require(bytes(_client).length > 0, "Client info cannot be empty");

        // Store the file metadata
        files[_cid] = File({
            cid: _cid,
            client: _client,
            timestamp: block.timestamp
        });

        // Emit an event
        emit FileUploaded(_cid, _client, block.timestamp);
    }

    // Function to retrieve file metadata by CID
    function getFile(string memory _cid) public view returns (string memory, string memory, uint256) {
        require(bytes(files[_cid].cid).length > 0, "File not found");

        File memory file = files[_cid];
        return (file.cid, file.client, file.timestamp);
    }
}
