import hashlib
import json
from datetime import datetime

class Block:
    def __init__(self, data, previous_hash=''):
        self.timestamp = datetime.now()
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": str(self.timestamp),
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block("Genesis Block", "0")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        previous_block = self.get_latest_block()
        new_block = Block(data, previous_block.hash)
        self.chain.append(new_block)
        return new_block

    def get_chain(self):
        return [{
            'timestamp': str(block.timestamp),
            'data': block.data,
            'previous_hash': block.previous_hash,
            'hash': block.hash
        } for block in self.chain] 