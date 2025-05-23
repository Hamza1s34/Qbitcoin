import unittest
from unittest.mock import MagicMock, patch, call
import sys
import types
import time
import threading
import socket
import ssl
import base64
import secrets
import tempfile
import os
from pathlib import Path

# Import modules under test
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Patch the import functions before importing security module
with patch('crypto.falcon.create_signature', return_value=b'mock_signature'), \
     patch('crypto.falcon.verify_signature', return_value=True):
    from core.network import p2p, sync, security

# Helper: Dummy blockchain and mempool for P2PNetwork
def get_dummy_blockchain():
    class DummyBlockchain:
        chain_id = 'testchain'
        current_height = 10
        best_hash = 'abc123'
        def get_block_by_height(self, h):
            class Block:
                def to_dict(self):
                    return {'height': h, 'hash': f'hash{h}', 'version': 1, 'prev_hash': 'prev', 'merkle_root': 'root', 'timestamp': 0, 'difficulty': 1, 'nonce': 0}
                @staticmethod
                def from_dict(d):
                    b = Block(); b.height = d['height']; b.hash = d['hash']; return b
                def validate(self): return True
            return Block() if h <= 10 else None
        def get_block_by_hash(self, h):
            return self.get_block_by_height(1)
        def add_block(self, b): return True
    return DummyBlockchain()

def get_dummy_mempool():
    class DummyMempool:
        def has_transaction(self, h):
            return False
        def add_transaction(self, d, bc):
            return True
        def get_transaction(self, h):
            class Tx:
                def to_dict(self_inner):
                    return {'hash': h}
            return Tx()
    return DummyMempool()

class TestP2PNetwork(unittest.TestCase):
    def setUp(self):
        self.blockchain = get_dummy_blockchain()
        self.mempool = get_dummy_mempool()
        # Patch config and logger
        patcher1 = patch('core.network.p2p.config', autospec=True)
        patcher2 = patch('core.network.p2p.logger', autospec=True)
        self.mock_config = patcher1.start()
        self.mock_logger = patcher2.start()
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.mock_config.P2P_PORT = 12345
        self.mock_config.MAX_PEERS = 8
        self.mock_config.BOOTSTRAP_NODES = ['127.0.0.1:12345']
        self.mock_config.PEER_PING_INTERVAL = 1
        self.mock_config.PEER_CONNECTION_TIMEOUT = 1
        self.mock_config.OUTBOUND_PEER_TARGET = 2
        self.mock_config.VERSION = '1.0.0'
        self.mock_config.DATA_DIR = Path(tempfile.gettempdir())
        self.network = p2p.P2PNetwork(self.blockchain, self.mempool)

    def test_peerinfo_to_dict_and_endpoint(self):
        peer = p2p.PeerInfo('127.0.0.1', 1234)
        d = peer.to_dict()
        self.assertEqual(d['address'], '127.0.0.1')
        self.assertEqual(peer.endpoint, '127.0.0.1:1234')

    def test_add_and_ban_peer(self):
        self.network._add_peer_address('1.2.3.4', 1111)
        self.assertIn('1.2.3.4:1111', self.network.peer_addresses)
        self.network._ban_peer('1.2.3.4', 1)
        self.assertTrue(self.network._is_banned('1.2.3.4'))
        time.sleep(1.1)
        self.assertFalse(self.network._is_banned('1.2.3.4'))

    def test_record_connection_failure_and_ban(self):
        for _ in range(3):
            self.network._record_connection_failure('5.6.7.8', 2222)
        self.assertTrue(self.network._is_banned('5.6.7.8'))

    def test_broadcast_transaction_and_block(self):
        # No peers, should warn
        tx = {'hash': 'tx1'}
        self.assertFalse(self.network.broadcast_transaction(tx))
        block = {'hash': 'b1', 'height': 1, 'version': 1, 'prev_hash': '', 'merkle_root': '', 'timestamp': 0, 'difficulty': 1, 'nonce': 0}
        self.assertFalse(self.network.broadcast_block(block))

    def test_get_connected_peers_and_stats(self):
        self.assertEqual(self.network.get_connected_peers(), [])
        stats = self.network.get_network_stats()
        self.assertIn('peers', stats)
        self.assertIn('uptime', stats)

    def test_sync_state_and_handlers(self):
        self.network.sync_state['syncing'] = False
        self.network.start_blockchain_sync()  # Should not sync if no better peer
        self.network.sync_state['syncing'] = True
        self.network.sync_state['sync_peer'] = '127.0.0.1:12345'
        self.network.sync_state['sync_height'] = 20
        self.network.sync_state['last_progress'] = time.time()
        self.network.sync_state['requested_blocks'] = set()
        self.network.sync_state['requested_headers'] = set()
        # Should not raise
        self.network._sync_blockchain()

    def test_message_handlers(self):
        # Use a dummy PeerConnection
        class DummyConn:
            peer_id = '1.1.1.1:1111'
            is_outbound = False
            def send_message(self, *a, **kw): pass
            host = '1.1.1.1'
            port = 1111
            def close(self, reason=None): pass
        conn = DummyConn()
        self.network.peers[conn.peer_id] = p2p.PeerInfo('1.1.1.1', 1111)
        self.network.active_connections[conn.peer_id] = conn
        # Test handshake
        self.network._handle_handshake(conn, {'chain_id': 'testchain', 'version': '1.0.0', 'height': 15, 'user_agent': 'ua', 'services': 1})
        # Test ping/pong
        self.network._handle_ping(conn, {'timestamp': time.time(), 'height': 12})
        self.network._handle_pong(conn, {'timestamp': time.time(), 'height': 13})
        # Test get_blocks/blocks
        self.network._handle_get_blocks(conn, {'start_height': 1})
        self.network._handle_blocks(conn, [{'height': 1, 'hash': 'h1', 'version': 1, 'prev_hash': '', 'merkle_root': '', 'timestamp': 0, 'difficulty': 1, 'nonce': 0}])
        # Test get_data
        self.network._handle_get_data(conn, {'items': [{'type': 2, 'hash': 'h1'}]})
        # Test transaction
        self.network._handle_transaction(conn, {'hash': 'tx1'})
        # Test inventory
        self.network._handle_inventory(conn, {'type': 2, 'hash': 'h2'})
        # Test get_peers/peers
        self.network._handle_get_peers(conn, {})
        self.network._handle_peers(conn, {'peers': [{'address': '8.8.8.8', 'port': 1234}]})
        # Test alert/reject
        self.network._handle_alert(conn, {'type': 'test', 'message': 'alert', 'signature': 'sig'})
        self.network._handle_reject(conn, {'message_type': 'msg', 'reason': 'bad', 'hash': 'h'})

class TestSyncModule(unittest.TestCase):
    def setUp(self):
        self.blockchain = get_dummy_blockchain()
        self.mempool = get_dummy_mempool()
        patcher1 = patch('core.network.sync.config', autospec=True)
        patcher2 = patch('core.network.sync.logger', autospec=True)
        self.mock_config = patcher1.start()
        self.mock_logger = patcher2.start()
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.mock_config.DIFFICULTY_ADJUSTMENT_BLOCKS = 10
        self.mock_config.VERSION = '1.0.0'
        self.sync_state = sync.SyncState(MagicMock(), self.blockchain)

    def test_start_and_stop_sync(self):
        self.assertTrue(self.sync_state.start_sync(15))
        self.sync_state.stop_sync()
        self.assertFalse(self.sync_state.syncing)

    def test_handle_headers_and_blocks(self):
        self.sync_state.start_sync(12)
        self.sync_state.handle_headers_message([
            {'height': 11, 'hash': 'h11'},
            {'height': 12, 'hash': 'h12'}
        ])
        self.sync_state.handle_blocks_message([
            {'height': 11, 'hash': 'h11'},
            {'height': 12, 'hash': 'h12'}
        ])
        self.assertIn(11, self.sync_state.headers_map)
        self.assertIn('h11', self.sync_state.downloaded_blocks)

    def test_get_status(self):
        status = self.sync_state.get_status()
        self.assertIn('syncing', status)
        self.assertIn('mode', status)

class TestSecurityModule(unittest.TestCase):
    def setUp(self):
        patcher = patch('core.network.security.logger', autospec=True)
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)
        self.node_id = 'node1'
        self.temp_dir = Path(tempfile.gettempdir()) / f'qbtc_test_{secrets.token_hex(4)}'
        self.temp_dir.mkdir(exist_ok=True)

    def test_message_encryption_basic(self):
        enc = security.MessageEncryption(session_key=b'0'*32)
        msg = b'hello world'
        encrypted = enc.encrypt_message(msg)
        decrypted = enc.decrypt_message(encrypted)
        self.assertEqual(decrypted, msg)

    def test_peer_auth_challenge(self):
        auth = security.PeerAuthentication(self.node_id)
        challenge = auth.generate_challenge('peer1')
        self.assertEqual(len(challenge), 32)
        # Simulate signature/verify with fallback
        with patch('crypto.falcon.verify_signature', return_value=True):
            self.assertTrue(auth.verify_challenge_response('peer1', challenge, b'sig', b'pub'))

    def test_secure_handshake(self):
        auth = security.PeerAuthentication(self.node_id)
        handshake = security.SecureHandshake(self.node_id, 'testchain', auth)
        msg = handshake.initiate_handshake('peer2')
        self.assertIn('challenge', msg)
        # Simulate response
        with patch.object(auth, 'verify_challenge_response', return_value=True):
            resp = handshake.process_handshake_response('peer2', {'chain_id': 'testchain', 'challenge_signature': base64.b64encode(b'sig').decode(), 'public_key': base64.b64encode(b'pub').decode(), 'ephemeral_key': base64.b64encode(b'pub').decode()})
            self.assertTrue(isinstance(resp, dict))

    def test_certificate_manager(self):
        cm = security.CertificateManager(self.temp_dir)
        if security.CRYPTOGRAPHY_AVAILABLE:
            self.assertTrue(cm.generate_ca_certificate())
            self.assertTrue(cm.generate_node_certificate(self.node_id))
            with open(cm.node_cert_path, 'rb') as f:
                cert_data = f.read()
            valid, reason = cm.verify_certificate(cert_data)
            self.assertTrue(valid)
            self.assertTrue(cm.revoke_certificate(cert_data))
        else:
            self.assertFalse(cm.generate_ca_certificate())

if __name__ == '__main__':
    unittest.main()
