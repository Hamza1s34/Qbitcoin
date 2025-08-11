#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import os
import time
import base64
from binascii import hexlify, a2b_base64
from collections import namedtuple
from decimal import Decimal
from typing import List

import click
import grpc
import simplejson as json
from google.protobuf.json_format import MessageToDict
from pyqrllib.pyqrllib import hstr2bin, bin2hstr
from qbitcoin.crypto.falcon import FalconSignature
from qbitcoin.crypto.AESHelper import AESHelper

from qbitcoin.core import config
from qbitcoin.core.Wallet import Wallet, WalletDecryptionError
from qbitcoin.core.misc.helper import parse_hexblob, parse_qaddress
from qbitcoin.core.MultiSigAddressState import MultiSigAddressState
from qbitcoin.core.txs.MessageTransaction import MessageTransaction
from qbitcoin.core.txs.SlaveTransaction import SlaveTransaction
from qbitcoin.core.txs.TokenTransaction import TokenTransaction
from qbitcoin.core.txs.Transaction import Transaction
from qbitcoin.core.txs.TransferTokenTransaction import TransferTokenTransaction
from qbitcoin.core.txs.TransferTransaction import TransferTransaction
from qbitcoin.core.txs.multisig.MultiSigCreate import MultiSigCreate
from qbitcoin.core.txs.multisig.MultiSigSpend import MultiSigSpend
from qbitcoin.generated import qbit_pb2_grpc, qbit_pb2
from qbitcoin.tools.wallet_creator import WalletCreator

ENV_QRL_WALLET_DIR = 'ENV_QRL_WALLET_DIR'

OutputMessage = namedtuple('OutputMessage', 'error address_items balance_items')
BalanceItem = namedtuple('BalanceItem', 'address balance')

CONNECTION_TIMEOUT = 5


class ModernWallet:
    """
    New wallet format that stores wallets in data/wallets/ directory
    with automatic encryption and structure similar to wallet_8756.json
    """
    
    def __init__(self, wallet_name=None):
        self.data_dir = config.user.data_dir
        self.wallets_dir = os.path.join(self.data_dir, 'wallets')
        os.makedirs(self.wallets_dir, exist_ok=True)
        
        if wallet_name is None:
            # Generate unique wallet name based on timestamp
            timestamp = int(time.time() * 1000)  # milliseconds
            wallet_name = f"wallet_{timestamp % 10000}.json"
        elif not wallet_name.endswith('.json'):
            wallet_name += '.json'
            
        self.wallet_path = os.path.join(self.wallets_dir, wallet_name)
        self.wallet_name = wallet_name
    
    def create_wallet(self, password=None):
        """Creates a new wallet with Falcon-512 address and automatic encryption"""
        if os.path.exists(self.wallet_path):
            click.echo(f"Wallet {self.wallet_name} already exists")
            return None
            
        # Generate Falcon-512 keypair
        private_key_bytes, public_key_bytes = FalconSignature.generate_keypair()
        address = WalletCreator.generate_address(public_key_bytes)
        
        # Get password for encryption
        if password is None:
            password = click.prompt('Enter password to encrypt wallet', hide_input=True, confirmation_prompt=True)
        
        # Encrypt private key
        cipher = AESHelper(password)
        encrypted_data = cipher.encrypt(private_key_bytes)
        
        # Create wallet structure similar to wallet_8756.json
        wallet_data = {
            "address": address,
            "algorithm": "falcon-512",
            "created_at": time.time(),
            "encrypted": True,
            "encryption_version": "1.0",
            "name": f"QBitcoin_Wallet_{int(time.time() * 1000)}",
            "private_key_encrypted": {
                "ciphertext": encrypted_data['ciphertext'],
                "encrypted": True,
                "nonce": encrypted_data['nonce'],
                "salt": encrypted_data['salt']
            },
            "private_key_size": len(private_key_bytes),
            "public_key": public_key_bytes.hex(),
            "public_key_size": len(public_key_bytes)
        }
        
        # Save wallet
        with open(self.wallet_path, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        return {
            'address': address,
            'wallet_path': self.wallet_path,
            'wallet_name': self.wallet_name,
            'public_key_bytes': public_key_bytes,
            'private_key_bytes': private_key_bytes  # Only returned during creation
        }
    
    def load_wallet(self, password):
        """Load and decrypt a wallet"""
        if not os.path.exists(self.wallet_path):
            return None
            
        with open(self.wallet_path, 'r') as f:
            wallet_data = json.load(f)
        
        # Decrypt private key
        cipher = AESHelper(password)
        encrypted_info = wallet_data['private_key_encrypted']
        private_key_bytes = cipher.decrypt_with_components(
            encrypted_info['ciphertext'],
            encrypted_info['nonce'],
            encrypted_info['salt']
        )
        
        public_key_bytes = bytes.fromhex(wallet_data['public_key'])
        
        return {
            'address': wallet_data['address'],
            'public_key_bytes': public_key_bytes,
            'private_key_bytes': private_key_bytes,
            'wallet_data': wallet_data
        }
    
    def list_wallets(self):
        """List all wallets in the wallets directory"""
        wallets = []
        if os.path.exists(self.wallets_dir):
            for filename in os.listdir(self.wallets_dir):
                if filename.endswith('.json'):
                    wallet_path = os.path.join(self.wallets_dir, filename)
                    try:
                        with open(wallet_path, 'r') as f:
                            wallet_data = json.load(f)
                        wallets.append({
                            'name': filename,
                            'address': wallet_data.get('address', 'Unknown'),
                            'created_at': wallet_data.get('created_at', 0),
                            'path': wallet_path
                        })
                    except Exception as e:
                        click.echo(f"Error reading wallet {filename}: {e}")
        return wallets


def get_modern_wallet_by_address_or_index(address_or_index, password=None):
    """Get wallet by address or index from modern wallet format"""
    modern_wallet = ModernWallet()
    wallets = modern_wallet.list_wallets()
    
    if not wallets:
        return None, None
    
    # Handle index
    if address_or_index.isdigit():
        index = int(address_or_index)
        if 0 <= index < len(wallets):
            wallet_info = wallets[index]
            modern_wallet.wallet_path = wallet_info['path']
            modern_wallet.wallet_name = wallet_info['name']
            
            if password is None:
                password = click.prompt('Enter wallet password', hide_input=True)
            
            wallet_data = modern_wallet.load_wallet(password)
            if wallet_data:
                return wallet_data['address'], {
                    'private_key_bytes': wallet_data['private_key_bytes'],
                    'public_key_bytes': wallet_data['public_key_bytes'],
                    'address': wallet_data['address']
                }
    
    # Handle address
    elif address_or_index.startswith('Q'):
        for wallet_info in wallets:
            if wallet_info['address'] == address_or_index:
                modern_wallet.wallet_path = wallet_info['path']
                modern_wallet.wallet_name = wallet_info['name']
                
                if password is None:
                    password = click.prompt('Enter wallet password', hide_input=True)
                
                wallet_data = modern_wallet.load_wallet(password)
                if wallet_data:
                    return wallet_data['address'], {
                        'private_key_bytes': wallet_data['private_key_bytes'],
                        'public_key_bytes': wallet_data['public_key_bytes'],
                        'address': wallet_data['address']
                    }
    
    return None, None


CONNECTION_TIMEOUT = 5


class CLIContext(object):
    def __init__(self, verbose, host, port_public, wallet_dir, output_json):
        self.verbose = verbose
        self.host = host
        self.port_public = port_public

        self.wallet_dir = os.path.abspath(wallet_dir)
        self.wallet_path = os.path.join(self.wallet_dir, 'wallet.json')
        self.output_json = output_json

    def get_stub_public_api(self):
        node_public_address = '{}:{}'.format(self.host, self.port_public)
        channel = grpc.insecure_channel(node_public_address)
        return qbit_pb2_grpc.PublicAPIStub(channel)


def _print_error(ctx, error_descr, wallets=None):
    # FIXME: Dead function
    if ctx.obj.output_json:
        if wallets is None:
            wallets = []
        msg = {'error': error_descr, 'wallets': wallets}
        click.echo(json.dumps(msg))
    else:
        print("ERROR: {}".format(error_descr))


def _serialize_output(ctx, addresses: List[OutputMessage], source_description) -> dict:
    if len(addresses) == 0:
        msg = {'error': 'No wallet found at {}'.format(source_description), 'wallets': []}
        return msg

    msg = {'error': None, 'wallets': []}

    for pos, item in enumerate(addresses):
        try:
            balance_unquarked = Decimal(_public_get_address_balance(ctx, item.qaddress)) / config.dev.quark_per_qbitcoin
            balance = '{:5.8f}'.format(balance_unquarked)
        except Exception as e:
            msg['error'] = str(e)
            balance = '?'

        msg['wallets'].append({
            'number': pos,
            'address': item.qaddress,
            'balance': balance,
            'signature_type': 'FALCON'
        })
    return msg


def _public_get_address_balance(ctx, address):
    stub = ctx.obj.get_stub_public_api()
    get_balance_req = qbit_pb2.GetBalanceReq(address=parse_qaddress(address))
    get_balance_resp = stub.GetBalance(get_balance_req, timeout=CONNECTION_TIMEOUT)
    return get_balance_resp.balance


def get_item_from_wallet(wallet, wallet_idx):
    if 0 <= wallet_idx < len(wallet.address_items):
        return wallet.address_items[wallet_idx]

    click.echo('Wallet index not found {}'.format(wallet_idx), color='yellow')
    return None


def _print_addresses(ctx, addresses: List[OutputMessage], source_description):
    def _normal(wallet):
        return "{:<8}{:<83}{:<13}".format(wallet['number'], wallet['address'], wallet['balance'])

    def _verbose(wallet):
        return "{:<8}{:<83}{:<13}{}".format(
            wallet['number'], wallet['address'], wallet['balance'], wallet['signature_type']
        )

    output = _serialize_output(ctx, addresses, source_description)
    if ctx.obj.output_json:
        output["location"] = source_description
        click.echo(json.dumps(output))
    else:
        if output['error'] and output['wallets'] == []:
            click.echo(output['error'])
        else:
            click.echo("Wallet at          : {}".format(source_description))
            if ctx.obj.verbose:
                header = "{:<8}{:<83}{:<13}{:<8}".format('Number', 'Address', 'Balance', 'Signature')
                divider = ('-' * 112)
            else:
                header = "{:<8}{:<83}{:<13}".format('Number', 'Address', 'Balance')
                divider = ('-' * 101)
            click.echo(header)
            click.echo(divider)

            for wallet in output['wallets']:
                if ctx.obj.verbose:
                    click.echo(_verbose(wallet))
                else:
                    click.echo(_normal(wallet))


def _public_get_address_balance(ctx, address):
    stub = ctx.obj.get_stub_public_api()
    get_address_state_req = qbit_pb2.GetAddressStateReq(address=parse_qaddress(address))
    get_optimized_address_state_resp = stub.GetOptimizedAddressState(get_address_state_req, timeout=CONNECTION_TIMEOUT)
    return get_optimized_address_state_resp.state.balance


def _select_wallet(ctx, address_or_index):
    """
    Updated to work with both legacy and modern wallet formats
    """
    try:
        # First try modern wallet format
        if address_or_index:
            address, falcon_data = get_modern_wallet_by_address_or_index(address_or_index)
            if address and falcon_data:
                return address, falcon_data
        
        # Fallback to legacy wallet format
        wallet = Wallet(wallet_path=ctx.obj.wallet_path)
        if len(wallet.address_items) == 0:
            click.echo('This command requires a local wallet')
            return None, None

        if wallet.encrypted:
            secret = click.prompt('The wallet is encrypted. Enter password', hide_input=True)
            wallet.decrypt(secret)

        # Handle empty input case
        if not address_or_index:
            # Return first wallet address by default if no address is provided
            if len(wallet.address_items) > 0:
                falcon = wallet.get_falcon_by_index(0)
                return wallet.address_items[0].qaddress, falcon
            return None, None

        if address_or_index.isdigit():
            address_or_index = int(address_or_index)
            addr_item = get_item_from_wallet(wallet, address_or_index)
            if addr_item:
                # Return Falcon-512 keypair
                falcon = wallet.get_falcon_by_index(address_or_index)
                return addr_item.qaddress, falcon

        elif address_or_index.startswith('Q'):
            for i, addr_item in enumerate(wallet.address_items):
                if address_or_index == addr_item.qaddress:
                    falcon = wallet.get_falcon_by_index(i)
                    return addr_item.qaddress, falcon
            click.echo('Source address not found in your wallet', color='yellow')
            quit(1)

        # If not a valid wallet address or index, treat as external address
        return parse_qaddress(address_or_index), None
    except Exception as e:
        click.echo("Error selecting wallet")
        click.echo(str(e))
        quit(1)


def _qbitcoin_to_quark(x: Decimal, base=Decimal(config.dev.quark_per_qbitcoin)) -> int:
    return int(Decimal(x * base).to_integral_value())


def _parse_dsts_amounts(addresses: str, amounts: str, token_decimals: int = 0, check_multi_sig_address=False):
    """
    'Qaddr1 Qaddr2...' -> [\\xcx3\\xc2, \\xc2d\\xc3]
    '10 10' -> [10e9, 10e9] (in quark)
    :param addresses:
    :param amounts:
    :return:
    """
    addresses_split = [parse_qaddress(addr, check_multi_sig_address) for addr in addresses.split(' ')]

    if token_decimals != 0:
        multiplier = Decimal(10 ** int(token_decimals))
        quark_amounts = [_qbitcoin_to_quark(Decimal(amount), base=multiplier) for amount in amounts.split(' ')]
    else:
        quark_amounts = [_qbitcoin_to_quark(Decimal(amount)) for amount in amounts.split(' ')]

    if len(addresses_split) != len(quark_amounts):
        raise Exception("dsts and amounts should be the same length")

    return addresses_split, quark_amounts


########################
########################
########################
########################

@click.version_option(version=config.dev.version, prog_name='QRL Command Line Interface')
@click.group()
@click.option('--verbose', '-v', default=False, is_flag=True, help='verbose output whenever possible')
@click.option('--host', default='127.0.0.1', help='remote host address             [127.0.0.1]')
@click.option('--port_pub', default=19009, help='remote port number (public api) [19009]')
@click.option('--wallet_dir', default='.', help='local wallet dir', envvar=ENV_QRL_WALLET_DIR)
@click.option('--json', default=False, is_flag=True, help='output in json')
@click.pass_context
def qrl(ctx, verbose, host, port_pub, wallet_dir, json):
    """
    QRL Command Line Interface
    """
    ctx.obj = CLIContext(verbose=verbose,
                         host=host,
                         port_public=port_pub,
                         wallet_dir=wallet_dir,
                         output_json=json)


@qrl.command(name='wallet_ls')
@click.pass_context
def wallet_ls(ctx):
    """
    Lists available wallets (both modern and legacy formats)
    """
    # List modern wallets
    modern_wallet = ModernWallet()
    modern_wallets = modern_wallet.list_wallets()
    
    if modern_wallets:
        click.echo("Modern Wallets (in data/wallets/):")
        click.echo("{:<8}{:<83}{:<13}{:<20}".format('Number', 'Address', 'Balance', 'Created'))
        click.echo('-' * 120)
        
        for i, wallet_info in enumerate(modern_wallets):
            try:
                balance_quark = _public_get_address_balance(ctx, wallet_info['address'])
                balance_qbitcoin = Decimal(balance_quark) / config.dev.quark_per_qbitcoin
                balance = '{:5.8f}'.format(balance_qbitcoin)
            except Exception:
                balance = '?'
            
            created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(wallet_info['created_at']))
            click.echo("{:<8}{:<83}{:<13}{:<20}".format(i, wallet_info['address'], balance, created_time))
    
    # List legacy wallets
    try:
        wallet = Wallet(wallet_path=ctx.obj.wallet_path)
        if len(wallet.address_items) > 0:
            click.echo("\nLegacy Wallet:")
            _print_addresses(ctx, wallet.address_items, ctx.obj.wallet_dir)
    except Exception:
        pass  # No legacy wallet found


@qrl.command(name='wallet_gen')
@click.pass_context
@click.option('--name', default=None, help='Name for the wallet file (optional)')
def wallet_gen(ctx, name):
    """
    Generates a new wallet with one Falcon-512 address in modern format
    """
    modern_wallet = ModernWallet(name)
    
    try:
        wallet_info = modern_wallet.create_wallet()
        if wallet_info:
            click.echo(f"Wallet created successfully: {wallet_info['wallet_name']}")
            click.echo(f"Address: {wallet_info['address']}")
            click.echo(f"Wallet stored in: {wallet_info['wallet_path']}")
            click.echo("Wallet is automatically encrypted with the password you provided.")
        else:
            click.echo("Failed to create wallet")
    except Exception as e:
        click.echo(f"Error creating wallet: {e}")
        quit(1)


@qrl.command(name='wallet_add')
@click.pass_context
@click.option('--name', default=None, help='Name for the new wallet file (optional)')
@click.option('--import-file', default=None, help='Path to external wallet file to import')
def wallet_add(ctx, name, import_file):
    """
    Creates a new wallet or imports an external wallet file into data/wallets directory
    """
    if import_file:
        # Import external wallet file
        import_external_wallet(import_file, name)
    else:
        # Create new wallet
        create_new_wallet(name)


def import_external_wallet(file_path, target_name=None):
    """
    Import an external wallet file into the data/wallets directory
    Supports different wallet formats and converts them to modern format
    """
    if not os.path.exists(file_path):
        click.echo(f"Error: Wallet file '{file_path}' not found")
        return
    
    try:
        # Read the external wallet file
        with open(file_path, 'r') as f:
            wallet_data = json.load(f)
        
        # Determine wallet format and extract key information
        address = None
        private_key_bytes = None
        public_key_bytes = None
        is_encrypted = False
        
        # Check if it's already our modern format
        if all(field in wallet_data for field in ['address', 'algorithm', 'encrypted', 'private_key_encrypted', 'public_key']):
            click.echo("Wallet is already in modern format, copying directly...")
            address = wallet_data['address']
            # Just copy as-is
            save_imported_wallet(wallet_data, file_path, target_name, address)
            return
        
        # Handle legacy QRL wallet format (version 0/1/2)
        elif 'addresses' in wallet_data or isinstance(wallet_data, list):
            click.echo("Detected legacy QRL wallet format...")
            address, private_key_bytes, public_key_bytes = handle_legacy_wallet_format(wallet_data)
        
        # Handle single address wallet format (like old format)
        elif 'qaddress' in wallet_data or ('address' in wallet_data and 'private_key' in wallet_data):
            click.echo("Detected single address wallet format...")
            address, private_key_bytes, public_key_bytes = handle_single_address_format(wallet_data)
        
        # Handle other custom formats
        else:
            click.echo("Detecting custom wallet format...")
            address, private_key_bytes, public_key_bytes = handle_custom_wallet_format(wallet_data)
        
        if not address or not private_key_bytes or not public_key_bytes:
            click.echo("Error: Could not extract wallet information from the file")
            return
        
        # Get password for new wallet encryption
        password = click.prompt('Enter password to encrypt the imported wallet', hide_input=True, confirmation_prompt=True)
        
        # Create modern wallet format
        modern_wallet_data = create_modern_wallet_data(address, private_key_bytes, public_key_bytes, password)
        
        # Save the wallet
        save_imported_wallet(modern_wallet_data, file_path, target_name, address)
        
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON format in wallet file")
    except Exception as e:
        click.echo(f"Error importing wallet: {e}")


def handle_legacy_wallet_format(wallet_data):
    """Handle legacy QRL wallet formats (version 0/1/2)"""
    addresses_list = wallet_data.get('addresses', wallet_data if isinstance(wallet_data, list) else [])
    
    if not addresses_list:
        raise Exception("No addresses found in legacy wallet")
    
    # Use first address
    addr_data = addresses_list[0]
    address = addr_data.get('address') or addr_data.get('qaddress')
    
    # Check if encrypted
    is_encrypted = wallet_data.get('encrypted', False) or addr_data.get('encrypted', False)
    
    if is_encrypted:
        password = click.prompt('Enter password to decrypt the wallet', hide_input=True)
        
        # Decrypt using legacy method
        cipher = AESHelper(password)
        private_key = cipher.decrypt(addr_data['private_key']).decode()
        public_key = cipher.decrypt(addr_data['public_key']).decode()
    else:
        private_key = addr_data['private_key']
        public_key = addr_data['public_key']
    
    # Convert to bytes
    private_key_bytes = base64.b64decode(private_key)
    public_key_bytes = base64.b64decode(public_key)
    
    return address, private_key_bytes, public_key_bytes


def handle_single_address_format(wallet_data):
    """Handle single address wallet formats"""
    address = wallet_data.get('qaddress') or wallet_data.get('address')
    
    # Check if encrypted
    is_encrypted = wallet_data.get('encrypted', False)
    
    if is_encrypted:
        password = click.prompt('Enter password to decrypt the wallet', hide_input=True)
        
        # Try different decryption methods
        if 'private_key_encrypted' in wallet_data:
            # Modern encryption format
            cipher = AESHelper(password)
            encrypted_info = wallet_data['private_key_encrypted']
            private_key_bytes = cipher.decrypt_with_components(
                encrypted_info['ciphertext'],
                encrypted_info['nonce'],
                encrypted_info['salt']
            )
        else:
            # Legacy encryption
            cipher = AESHelper(password)
            private_key_bytes = cipher.decrypt(wallet_data['private_key'])
    else:
        # Not encrypted
        if 'private_key' in wallet_data:
            if isinstance(wallet_data['private_key'], str):
                try:
                    private_key_bytes = base64.b64decode(wallet_data['private_key'])
                except:
                    private_key_bytes = bytes.fromhex(wallet_data['private_key'])
            else:
                private_key_bytes = wallet_data['private_key']
        else:
            raise Exception("No private key found in wallet")
    
    # Get public key
    if 'public_key' in wallet_data:
        if isinstance(wallet_data['public_key'], str):
            try:
                public_key_bytes = base64.b64decode(wallet_data['public_key'])
            except:
                public_key_bytes = bytes.fromhex(wallet_data['public_key'])
        else:
            public_key_bytes = wallet_data['public_key']
    else:
        raise Exception("No public key found in wallet")
    
    return address, private_key_bytes, public_key_bytes


def handle_custom_wallet_format(wallet_data):
    """Handle custom or unknown wallet formats"""
    # Try to find address, private key, and public key in various field names
    address_fields = ['address', 'qaddress', 'addr', 'wallet_address']
    private_key_fields = ['private_key_hex', 'private_key', 'privatekey', 'priv_key', 'secret_key', 'sk']
    public_key_fields = ['public_key_hex', 'public_key', 'publickey', 'pub_key', 'pk']
    
    address = None
    private_key = None
    public_key = None
    
    # Find address
    for field in address_fields:
        if field in wallet_data:
            address = wallet_data[field]
            break
    
    # Find private key
    for field in private_key_fields:
        if field in wallet_data:
            private_key = wallet_data[field]
            break
    
    # Find public key
    for field in public_key_fields:
        if field in wallet_data:
            public_key = wallet_data[field]
            break
    
    if not private_key or not public_key:
        raise Exception("Could not find required fields (private_key, public_key) in wallet file")
    
    # Check if encrypted (look for common encryption indicators)
    is_encrypted = wallet_data.get('encrypted', False) or any(
        'encrypt' in str(key).lower() for key in wallet_data.keys()
    )
    
    if is_encrypted:
        password = click.prompt('Enter password to decrypt the wallet', hide_input=True)
        cipher = AESHelper(password)
        
        # Try to decrypt
        try:
            if isinstance(private_key, str) and len(private_key) > 100:  # Likely encrypted
                private_key_bytes = cipher.decrypt(private_key)
            else:
                # Assume it's hex and try to convert
                private_key_bytes = bytes.fromhex(private_key)
        except Exception as e:
            click.echo(f"Decryption failed: {e}")
            raise Exception("Could not decrypt private key")
    else:
        # Convert to bytes from hex or base64
        if isinstance(private_key, str):
            try:
                # Try hex first (more common for raw keys)
                private_key_bytes = bytes.fromhex(private_key)
            except ValueError:
                try:
                    # Try base64 if hex fails
                    private_key_bytes = base64.b64decode(private_key)
                except Exception:
                    raise Exception("Could not decode private key (not valid hex or base64)")
        else:
            private_key_bytes = private_key
    
    # Convert public key to bytes
    if isinstance(public_key, str):
        try:
            # Try hex first
            public_key_bytes = bytes.fromhex(public_key)
        except ValueError:
            try:
                # Try base64 if hex fails
                public_key_bytes = base64.b64decode(public_key)
            except Exception:
                raise Exception("Could not decode public key (not valid hex or base64)")
    else:
        public_key_bytes = public_key
    
    # Generate address if not found
    if not address:
        address = WalletCreator.generate_address(public_key_bytes)
    
    return address, private_key_bytes, public_key_bytes


def create_modern_wallet_data(address, private_key_bytes, public_key_bytes, password):
    """Create modern wallet format data structure"""
    # Encrypt private key
    cipher = AESHelper(password)
    encrypted_data = cipher.encrypt(private_key_bytes)
    
    # Create modern wallet structure
    wallet_data = {
        "address": address,
        "algorithm": "falcon-512",
        "created_at": time.time(),
        "encrypted": True,
        "encryption_version": "1.0",
        "name": f"QBitcoin_Wallet_{int(time.time() * 1000)}",
        "private_key_encrypted": {
            "ciphertext": encrypted_data['ciphertext'],
            "encrypted": True,
            "nonce": encrypted_data['nonce'],
            "salt": encrypted_data['salt']
        },
        "private_key_size": len(private_key_bytes),
        "public_key": public_key_bytes.hex(),
        "public_key_size": len(public_key_bytes)
    }
    
    return wallet_data


def save_imported_wallet(wallet_data, source_path, target_name, address):
    """Save the imported wallet to data/wallets directory"""
    # Generate target name
    if not target_name:
        # Extract filename without path and extension
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        target_name = f"{base_name}_imported"
    
    if not target_name.endswith('.json'):
        target_name += '.json'
    
    # Create target path in data/wallets
    modern_wallet = ModernWallet()
    target_path = os.path.join(modern_wallet.wallets_dir, target_name)
    
    # Check if target already exists
    if os.path.exists(target_path):
        overwrite = click.confirm(f"Wallet '{target_name}' already exists. Overwrite?")
        if not overwrite:
            click.echo("Import cancelled")
            return
    
    # Save wallet to target location
    with open(target_path, 'w') as f:
        json.dump(wallet_data, f, indent=2)
    
    click.echo(f"Wallet imported successfully:")
    click.echo(f"  Source: {source_path}")
    click.echo(f"  Target: {target_path}")
    click.echo(f"  Address: {address}")
    click.echo(f"  Format: Modern encrypted wallet")


def create_new_wallet(name=None):
    """
    Create a new wallet in modern format
    """
    modern_wallet = ModernWallet(name)
    
    try:
        wallet_info = modern_wallet.create_wallet()
        if wallet_info:
            click.echo(f"New wallet created: {wallet_info['wallet_name']}")
            click.echo(f"Address: {wallet_info['address']}")
            click.echo(f"Wallet stored in: {wallet_info['wallet_path']}")
            click.echo("Wallet is automatically encrypted with the password you provided.")
        else:
            click.echo("Failed to create wallet")
    except Exception as e:
        click.echo(f"Error creating wallet: {e}")
        quit(1)


@qrl.command(name='balance')
@click.argument('address', required=True)
@click.pass_context
def balance(ctx, address):
    """
    Get the balance of a QRL address
    """
    try:
        # Validate the address format
        try:
            _ = parse_qaddress(address)
        except Exception:
            click.echo(f"Invalid QRL address format: {address}")
            return

        # Get balance from node
        balance_quark = _public_get_address_balance(ctx, address)
        
        # Convert from quark to Qbitcoin
        balance_qbitcoin = Decimal(balance_quark) / config.dev.quark_per_qbitcoin
        
        # Display the balance
        click.echo(f"Address: {address}")
        click.echo(f"Balance: {balance_qbitcoin} Qbitcoin ({balance_quark} quark)")
        
    except Exception as e:
        click.echo(f"Error retrieving balance: {e}")


@qrl.command(name='wallet_secret')
@click.option('--wallet-idx', default=0, prompt=True, help='Index of modern wallet or address')
@click.pass_context
def wallet_secret(ctx, wallet_idx):
    """
    Provides the private key information of the given wallet
    """
    try:
        # Try to get modern wallet by index
        modern_wallet = ModernWallet()
        wallets = modern_wallet.list_wallets()
        
        if wallets and str(wallet_idx).isdigit() and 0 <= int(wallet_idx) < len(wallets):
            wallet_info = wallets[int(wallet_idx)]
            modern_wallet.wallet_path = wallet_info['path']
            modern_wallet.wallet_name = wallet_info['name']
            
            password = click.prompt('Enter wallet password', hide_input=True)
            wallet_data = modern_wallet.load_wallet(password)
            
            if wallet_data:
                click.echo('Wallet Address  : {}'.format(wallet_data['address']))
                click.echo('Private Key     : {}'.format(wallet_data['private_key_bytes'].hex()))
                click.echo('Public Key      : {}'.format(wallet_data['public_key_bytes'].hex()))
                return
        
        # Fallback to legacy wallet
        wallet = Wallet(wallet_path=ctx.obj.wallet_path)
        if wallet.encrypted:
            secret = click.prompt('The wallet is encrypted. Enter password', hide_input=True)
            wallet.decrypt(secret)

        address_item = get_item_from_wallet(wallet, wallet_idx)
        if address_item:
            click.echo('Wallet Address  : {}'.format(address_item.qaddress))
            falcon_data = wallet.get_falcon_by_index(wallet_idx)
            if falcon_data:
                click.echo('Private Key     : {}'.format(falcon_data['private_key_bytes'].hex()))
                click.echo('Public Key      : {}'.format(falcon_data['public_key_bytes'].hex()))
        else:
            click.echo('Wallet not found')
            
    except Exception as e:
        click.echo(f"Error: {e}")
        quit(1)


@qrl.command(name='wallet_rm')
@click.option('--wallet-idx', type=int, prompt=True, help='index of modern wallet')
@click.option('--skip-confirmation', default=False, is_flag=True, prompt=False, help='skip the confirmation prompt')
@click.pass_context
def wallet_rm(ctx, wallet_idx, skip_confirmation):
    """
    Removes a modern wallet file.

    Warning! Use with caution. Removing a wallet file will result in 
    loss of access to the address unless you have backed up the private key.
    """
    try:
        modern_wallet = ModernWallet()
        wallets = modern_wallet.list_wallets()
        
        if not wallets or wallet_idx >= len(wallets) or wallet_idx < 0:
            click.echo(f'Wallet index {wallet_idx} not found')
            return
            
        wallet_info = wallets[wallet_idx]
        
        if not skip_confirmation:
            click.echo(f'You are about to remove wallet [{wallet_idx}]: {wallet_info["address"]}')
            click.echo('Warning! By continuing, you risk complete loss of access to this address')
            click.echo('unless you have backed up the private key.')
            click.confirm('Do you want to continue?', abort=True)
        
        os.remove(wallet_info['path'])
        click.echo(f'Wallet {wallet_info["name"]} has been removed')
        
    except Exception as e:
        click.echo(f"Error removing wallet: {e}")
        quit(1)


@qrl.command(name='tx_inspect')
@click.option('--txblob', type=str, default='', prompt=True, help='transaction blob')
@click.pass_context
def tx_inspect(ctx, txblob):
    """
    Inspected a transaction blob
    """
    tx = None
    try:
        txbin = parse_hexblob(txblob)
        pbdata = qbit_pb2.Transaction()
        pbdata.ParseFromString(txbin)
        tx = Transaction.from_pbdata(pbdata)
    except Exception as e:
        click.echo("tx blob is not valid")
        quit(1)

    tmp_json = tx.to_json()
    # FIXME: binary fields are represented in base64. Improve output
    print(tmp_json)


@qrl.command(name='tx_push')
@click.option('--txblob', type=str, default='', help='transaction blob (unsigned)')
@click.pass_context
def tx_push(ctx, txblob):
    """
    Sends a signed transaction blob to a node
    """
    tx = None
    try:
        txbin = parse_hexblob(txblob)
        pbdata = qbit_pb2.Transaction()
        pbdata.ParseFromString(txbin)
        tx = Transaction.from_pbdata(pbdata)
    except Exception as e:
        click.echo("tx blob is not valid")
        quit(1)

    tmp_json = tx.to_json()
    # FIXME: binary fields are represented in base64. Improve output
    print(tmp_json)
    if len(tx.signature) == 0:
        click.echo('Signature missing')
        quit(1)

    stub = ctx.obj.get_stub_public_api()
    pushTransactionReq = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
    pushTransactionResp = stub.PushTransaction(pushTransactionReq, timeout=CONNECTION_TIMEOUT)
    print(pushTransactionResp.error_code)


@qrl.command(name='tx_message')
@click.option('--src', type=str, default='', prompt=True, help='signer QRL address')
@click.option('--master', type=str, default='', prompt=True, help='master QRL address')
@click.option('--addr_to', type=str, default='', prompt=True, help='QRL Address receiving this message (optional)')
@click.option('--message', type=str, prompt=True, help='Message (max 80 bytes)')
@click.option('--fee', type=Decimal, default=0.0, prompt=True, help='fee in Qbitcoin')
@click.pass_context
def tx_message(ctx, src, master, addr_to, message, fee):
    """
    Message Transaction
    """
    try:
        _, src_falcon = _select_wallet(ctx, src)
        if not src_falcon:
            click.echo("A local wallet is required to sign the transaction")
            quit(1)

        address_src_pk = src_falcon['public_key_bytes']

        message = message.encode()
        if addr_to:
            addr_to = parse_qaddress(addr_to, False)
        else:
            addr_to = None

        master_addr = None
        if master:
            master_addr = parse_qaddress(master)
        fee_quark = _qbitcoin_to_quark(fee)
    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)

    try:
        stub = ctx.obj.get_stub_public_api()
        tx = MessageTransaction.create(message_hash=message,
                                       addr_to=addr_to,
                                       fee=fee_quark,
                                       xmss_pk=address_src_pk,
                                       master_addr=master_addr)
        # Sign with Falcon-512
        tx_data = tx.get_data_bytes()
        signature = FalconSignature.sign_message(tx_data, src_falcon['private_key_bytes'])
        tx._data.signature = signature

        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)

        print(push_transaction_resp)
    except Exception as e:
        print("Error {}".format(str(e)))


@qrl.command(name='tx_multi_sig_create')
@click.option('--src', type=str, default='', prompt=True, help='source QRL address')
@click.option('--master', type=str, default='', prompt=True, help='master QRL address')
@click.option('--threshold', default=0, prompt=True, help='Threshold')
@click.option('--fee', type=Decimal, default=0.0, prompt=True, help='fee in Qbitcoin')
@click.option('--signature_index', default=1, prompt=True, help='Signature Index for Falcon-512')
@click.pass_context
def tx_multi_sig_create(ctx, src, master, threshold, fee, signature_index):
    """
    Creates Multi Sig Create Transaction, that results into the formation of new multi_sig_address if accepted.
    """
    signatories = []
    weights = []
    while True:
        address = click.prompt('Address of Signatory ', default='')
        if address == '':
            break
        weight = int(click.prompt('Weight '))
        signatories.append(parse_qaddress(address))
        weights.append(weight)

    try:
        _, src_falcon = _select_wallet(ctx, src)
        if not src_falcon:
            click.echo("A local wallet is required to sign the transaction")
            quit(1)

        address_src_pk = src_falcon['public_key_bytes']

         

        master_addr = None
        if master:
            master_addr = parse_qaddress(master)
        # FIXME: This could be problematic. Check
        fee_quark = _qbitcoin_to_quark(fee)

    except KeyboardInterrupt:
        click.echo("Terminated by user")
        quit(1)
    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)

    try:
        stub = ctx.obj.get_stub_public_api()
        tx = MultiSigCreate.create(signatories=signatories,
                                   weights=weights,
                                   threshold=threshold,
                                   fee=fee_quark,
                                   xmss_pk=address_src_pk,
                                   master_addr=master_addr)

        # Sign with Falcon-512
        tx_data = tx.get_data_bytes()
        signature = FalconSignature.sign_message(tx_data, src_falcon['private_key_bytes'])
        tx._data.signature = signature
        tx._data.nonce = signature_index

        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)

        print(push_transaction_resp.error_code)
        print('Multi sig Address Q{}'.format(bin2hstr(MultiSigAddressState.generate_multi_sig_address(tx.txhash))))
    except Exception as e:
        print("Error {}".format(str(e)))


@qrl.command(name='tx_multi_sig_spend')
@click.option('--src', type=str, default='', prompt=True, help='signer QRL address')
@click.option('--master', type=str, default='', help='master QRL address')
@click.option('--multi_sig_address', type=str, default='', prompt=True, help='signer Multi Sig Address')
@click.option('--dsts', type=str, prompt=True, help='List of destination addresses')
@click.option('--amounts', type=str, prompt=True, help='List of amounts to transfer (Qbitcoin)')
@click.option('--expiry_block_number', type=int, prompt=True, help='Expiry Blocknumber')
@click.option('--fee', type=Decimal, default=0.0, prompt=True, help='fee in Qbitcoin')
@click.option('--signature_index', default=1, help='Signature Index for Falcon-512')
@click.pass_context
def tx_multi_sig_spend(ctx, src, master, multi_sig_address, dsts, amounts, expiry_block_number, fee, signature_index):
    """
    Transfer coins from src to dsts
    """
    address_src_pk = None
    master_addr = None

    addresses_dst = []
    quark_amounts = []
    fee_quark = []

    signing_object = None

    try:
        # Retrieve signing object
        selected_wallet = _select_wallet(ctx, src)
        if selected_wallet is None or len(selected_wallet) != 2:
            click.echo("A wallet was not found")
            quit(1)

        _, src_falcon = selected_wallet

        if not src_falcon:
            click.echo("A local wallet is required to sign the transaction")
            quit(1)

        address_src_pk = src_falcon['public_key_bytes']

        

        signing_object = src_falcon

        # Get and validate other inputs
        if master:
            master_addr = parse_qaddress(master)

        addresses_dst, quark_amounts = _parse_dsts_amounts(dsts, amounts, check_multi_sig_address=True)
        fee_quark = _qbitcoin_to_quark(fee)
    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)
    multi_sig_address = bytes(hstr2bin(multi_sig_address[1:]))
    try:
        # MultiSigSpend transaction
        tx = MultiSigSpend.create(multi_sig_address=multi_sig_address,
                                  addrs_to=addresses_dst,
                                  amounts=quark_amounts,
                                  expiry_block_number=expiry_block_number,
                                  fee=fee_quark,
                                  xmss_pk=address_src_pk,
                                  master_addr=master_addr)

        # Sign transaction
        tx.sign(signing_object)

        if not tx.validate():
            print("It was not possible to validate the signature")
            quit(1)

        print("\nTransaction Blob (signed): \n")
        txblob = tx.pbdata.SerializeToString()
        txblobhex = hexlify(txblob).decode()
        print(txblobhex)

        # Push transaction
        print()
        print("Sending to a QRL Node...")
        stub = ctx.obj.get_stub_public_api()
        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)

        # Print result
        print(push_transaction_resp)
    except Exception as e:
        print("Error {}".format(str(e)))


def base64tohex(data):
    return hexlify(a2b_base64(data))


def tx_unbase64(tx_json_str):
    """
    Convert base64 encoded fields in transaction JSON to hex format
    """
    try:
        tx_json = json.loads(tx_json_str)
        
        # Convert publicKey if present
        if "publicKey" in tx_json:
            tx_json["publicKey"] = base64tohex(tx_json["publicKey"])
        
        # Convert signature if present
        if "signature" in tx_json:
            tx_json["signature"] = base64tohex(tx_json["signature"])
        
        # Convert transactionHash if present
        if "transactionHash" in tx_json:
            tx_json["transactionHash"] = base64tohex(tx_json["transactionHash"])
        
        # Convert transfer addresses if present
        if "transfer" in tx_json and "addrsTo" in tx_json["transfer"]:
            tx_json["transfer"]["addrsTo"] = [base64tohex(v) for v in tx_json["transfer"]["addrsTo"]]
        
        return json.dumps(tx_json, indent=True, sort_keys=True)
    except Exception as e:
        # If conversion fails, return the original JSON string
        click.echo(f"Warning: Could not convert transaction JSON: {e}")
        return tx_json_str


@qrl.command(name='tx_transfer')
@click.option('--src', type=str, default='', prompt=True, help='signer qbitcoin  address')
@click.option('--master', type=str, default='', help='master QRL address')
@click.option('--dsts', type=str, prompt=True, help='List of destination addresses')
@click.option('--amounts', type=str, prompt=True, help='List of amounts to transfer (Qbit)')
@click.option('--message_data', type=str, prompt=True, help='Message (Optional)')
@click.option('--fee', type=Decimal, default=0.0, prompt=True, help='fee in qbit ')
@click.pass_context
def tx_transfer(ctx, src, master, dsts, amounts, message_data, fee):
    """
    Transfer coins from src to dsts
    """
    try:
        # Retrieve signing object
        src_addr, src_falcon = _select_wallet(ctx, src)
        if src_addr is None or src_falcon is None:
            click.echo("A valid wallet is required to sign the transaction")
            quit(1)

        # Get and validate other inputs
        master_addr = None
        if master:
            master_addr = parse_qaddress(master)
        
        addresses_dst, quark_amounts = _parse_dsts_amounts(dsts, amounts, check_multi_sig_address=True)
        fee_quark = _qbitcoin_to_quark(fee)
        
        # Encode message data
        if message_data:
            message_data_bytes = message_data.encode()
        else:
            message_data_bytes = b''

    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)

    try:
        # Create transaction manually like in the working script - BYPASS TransferTransaction.create()
        tx = TransferTransaction()
        tx._data.public_key = src_falcon['public_key_bytes']
        
        # Add destination addresses and amounts
        for addr, amount in zip(addresses_dst, quark_amounts):
            tx._data.transfer.addrs_to.append(addr)
            tx._data.transfer.amounts.append(amount)
        
        # Add message data if provided
        if message_data_bytes:
            tx._data.transfer.message_data = message_data_bytes
        
        # Set fee
        tx._data.fee = fee_quark
        
        # CRITICAL: Set master_addr directly to bypass QRLHelper issues
        # Use source address bytes (remove 'Q' prefix and convert to bytes)
        if src_addr.startswith('Q'):
            addr_hex = src_addr[1:]
            tx._data.master_addr = bytes.fromhex(addr_hex)
        else:
            click.echo("Invalid source address format")
            quit(1)
        
        # Get transaction data hash for signing (MUST be done before setting signature)
        tx_data_hash = tx.get_data_hash()
        
        # Sign with Falcon-512
        click.echo("Signing transaction...")
        signature = FalconSignature.sign_message(tx_data_hash, src_falcon['private_key_bytes'])
        click.echo(f"DEBUG: Generated signature length: {len(signature)} bytes")
        click.echo(f"DEBUG: Signature hash: {signature[:20].hex()}...")
        tx._data.signature = signature
        
        # Update transaction hash after signing
        tx.update_txhash()
        
        # Print transaction JSON - handle potential JSON conversion errors
        try:
            txjson = tx_unbase64(tx.to_json())
            print("Transaction JSON:")
            print(txjson)
        except Exception as json_error:
            print(f"Warning: Could not format transaction JSON: {json_error}")
            print("Raw transaction data available")
        
        # Use the same validation as the working script
        if not validate_transaction_like_script(tx):
            click.echo("Transaction validation failed")
            quit(1)
        
        click.echo("Transaction validation passed")
        
        # Print transaction blob
        txblob = tx.pbdata.SerializeToString()
        txblobhex = hexlify(txblob).decode()
        print(f"\nTransaction Blob (signed): \n{txblobhex}")
        
        # Push transaction to node
        print("\nSending to Qbitcoin Node...")
        stub = ctx.obj.get_stub_public_api()
        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)
        
        # Print result using the same logic as the working script
        if push_transaction_resp.error_code == qbit_pb2.PushTransactionResp.SUBMITTED:
            click.echo("Transaction successfully submitted!")
            click.echo(f"Transaction hash: {bin2hstr(tx.txhash)}")
        else:
            click.echo(f"Transaction submission failed: {push_transaction_resp.error_description}")
            
    except Exception as e:
        print("Error {}".format(str(e)))
        import traceback
        traceback.print_exc()


def validate_transaction_like_script(tx):
    """
    Use the exact same validation as the working create_transaction.py script
    """
    if not tx._data.transfer.addrs_to:
        print("Transaction has no recipient addresses")
        return False
    
    if not tx._data.transfer.amounts:
        print("Transaction has no amounts")
        return False
    
    for amount in tx._data.transfer.amounts:
        if amount <= 0:
            print(f"Invalid amount: {amount}")
            return False
    
    if tx._data.fee < 0:
        print(f"Invalid fee: {tx._data.fee}")
        return False
    
    if not tx._data.signature:
        print("Transaction is not signed")
        return False
    
    return True


@qrl.command(name='tx_token')
@click.option('--src', type=str, default='', prompt=True, help='source QRL address')
@click.option('--master', type=str, default='', prompt=True, help='master QRL address')
@click.option('--symbol', default='', prompt=True, help='Symbol Name')
@click.option('--name', default='', prompt=True, help='Token Name')
@click.option('--owner', default='', prompt=True, help='Owner QRL address')
@click.option('--decimals', default=0, prompt=True, help='decimals')
@click.option('--fee', type=Decimal, default=0.0, prompt=True, help='fee in Qbitcoin')
@click.pass_context
def tx_token(ctx, src, master, symbol, name, owner, decimals, fee):
    """
    Create Token Transaction, that results into the formation of new token if accepted.
    """

    initial_balances = []

    if decimals > 19:
        click.echo("The number of decimal cannot exceed 19 under any possible configuration")
        quit(1)

    while True:
        address = click.prompt('Address ', default='')
        if address == '':
            break
        amount = int(click.prompt('Amount ')) * (10 ** int(decimals))
        initial_balances.append(qbit_pb2.AddressAmount(address=parse_qaddress(address),
                                                      amount=amount))

    try:
        src_addr, src_falcon = _select_wallet(ctx, src)
        if src_addr is None or src_falcon is None:
            click.echo("A valid wallet is required to sign the transaction")
            quit(1)

        address_src_pk = src_falcon['public_key_bytes']

        address_owner = parse_qaddress(owner)
        master_addr = None
        if master:
            master_addr = parse_qaddress(master)
        # FIXME: This could be problematic. Check
        fee_quark = _qbitcoin_to_quark(fee)

        if len(name) > config.dev.max_token_name_length:
            raise Exception("Token name must be quarkter than {} chars".format(config.dev.max_token_name_length))
        if len(symbol) > config.dev.max_token_symbol_length:
            raise Exception("Token symbol must be quarkter than {} chars".format(config.dev.max_token_symbol_length))

    except KeyboardInterrupt:
        click.echo("Terminated by user")
        quit(1)
    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)

    try:
        stub = ctx.obj.get_stub_public_api()
        tx = TokenTransaction.create(symbol=symbol.encode(),
                                     name=name.encode(),
                                     owner=address_owner,
                                     decimals=decimals,
                                     initial_balances=initial_balances,
                                     fee=fee_quark,
                                     xmss_pk=address_src_pk,
                                     master_addr=master_addr)

        # Sign with Falcon-512
        tx_data = tx.get_data_bytes()
        signature = FalconSignature.sign_message(tx_data, src_falcon['private_key_bytes'])
        tx._data.signature = signature

        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)

        print(push_transaction_resp.error_code)
    except Exception as e:
        print("Error {}".format(str(e)))


@qrl.command(name='tx_transfertoken')
@click.option('--src', type=str, default='', prompt=True, help='source QRL address')
@click.option('--master', type=str, default='', prompt=True, help='master QRL address')
@click.option('--token_txhash', default='', prompt=True, help='Token Txhash')
@click.option('--dsts', type=str, prompt=True, help='List of destination addresses')
@click.option('--amounts', type=str, prompt=True, help='List of amounts to transfer (Qbitcoin)')
@click.option('--decimals', default=0, prompt=True, help='decimals')
@click.option('--fee', type=Decimal, default=0.0, prompt=True, help='fee in Qbitcoin')
@click.pass_context
def tx_transfertoken(ctx, src, master, token_txhash, dsts, amounts, decimals, fee):
    """
    Create Transfer Token Transaction, which moves tokens from src to dst.
    """

    if decimals > 19:
        click.echo("The number of decimal cannot exceed 19 under any configuration")
        quit(1)

    try:
        addresses_dst, quark_amounts = _parse_dsts_amounts(dsts, amounts, token_decimals=decimals)
        bin_token_txhash = parse_hexblob(token_txhash)
        master_addr = None
        if master:
            master_addr = parse_qaddress(master)
        # FIXME: This could be problematic. Check
        fee_quark = _qbitcoin_to_quark(fee)

        _, src_falcon = _select_wallet(ctx, src)
        if not src_falcon:
            click.echo("A local wallet is required to sign the transaction")
            quit(1)

        address_src_pk = src_falcon['public_key_bytes']

    except KeyboardInterrupt:
        click.echo("Terminated by user")
        quit(1)
    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)

    try:
        stub = ctx.obj.get_stub_public_api()
        tx = TransferTokenTransaction.create(token_txhash=bin_token_txhash,
                                             addrs_to=addresses_dst,
                                             amounts=quark_amounts,
                                             fee=fee_quark,
                                             xmss_pk=address_src_pk,
                                             master_addr=master_addr)
        # Sign with Falcon-512
        tx_data = tx.get_data_bytes()
        signature = FalconSignature.sign_message(tx_data, src_falcon['private_key_bytes'])
        tx._data.signature = signature

        push_transaction_req = qbit_pb2.PushTransactionReq(transaction_signed=tx.pbdata)
        push_transaction_resp = stub.PushTransaction(push_transaction_req, timeout=CONNECTION_TIMEOUT)

        print(push_transaction_resp.error_code)
    except Exception as e:
        print("Error {}".format(str(e)))


@qrl.command(name='slave_tx_generate')
@click.option('--src', type=str, default='', prompt=True, help='source address or index')
@click.option('--master', type=str, default='', prompt=True, help='master QRL address')
@click.option('--number_of_slaves', default=0, type=int, prompt=True, help='Number of slaves addresses')
@click.option('--access_type', default=0, type=int, prompt=True, help='0 - All Permission, 1 - Only Mining Permission')
@click.option('--fee', type=Decimal, default=0.0, prompt=True, help='fee (Qbitcoin)')
@click.option('--pk', default=0, prompt=False, help='public key (when local wallet is missing)')
@click.option('--signature_index', default=1, prompt=False, help='Signature Index for Falcon-512')
@click.pass_context
def slave_tx_generate(ctx, src, master, number_of_slaves, access_type, fee, pk, signature_index):
    """
    Generates Slave Transaction for the wallet
    """
    try:
        _, src_falcon = _select_wallet(ctx, src)

        
        if src_falcon:
            address_src_pk = src_falcon['public_key_bytes']
        else:
            address_src_pk = pk.encode()

        master_addr = None
        if master:
            master_addr = parse_qaddress(master)
        fee_quark = _qbitcoin_to_quark(fee)
    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)

    slave_xmss = []
    slave_pks = []
    access_types = []
    slave_xmss_seed = []
    if number_of_slaves > 100:
        click.echo("Error: Max Limit for the number of slaves is 100")
        quit(1)

    for i in range(number_of_slaves):
        print("Generating Slave #" + str(i + 1))
        private_key_bytes, public_key_bytes = FalconSignature.generate_keypair()
        slave_pks.append(public_key_bytes)
        access_types.append(access_type)
        # Store key pairs for later use
        from qbitcoin.tools.wallet_creator import WalletCreator
        slave_address = WalletCreator.generate_address(public_key_bytes)
        slave_xmss.append({
            'private_key_bytes': private_key_bytes,
            'public_key_bytes': public_key_bytes,
            'address': slave_address
        })
        print("Successfully Generated Slave %s/%s" % (str(i + 1), number_of_slaves))

    try:
        tx = SlaveTransaction.create(slave_pks=slave_pks,
                                     access_types=access_types,
                                     fee=fee_quark,
                                     xmss_pk=address_src_pk,
                                     master_addr=master_addr)
        
        # Sign with Falcon-512
        if src_falcon:
            tx_data = tx.get_data_bytes()
            signature = FalconSignature.sign_message(tx_data, src_falcon['private_key_bytes'])
            tx._data.signature = signature
           
            
        # Save slave information to JSON file
        slave_info = []
        for slave in slave_xmss:
            slave_info.append({
                'address': slave['address'],
                'pk': bin2hstr(slave['public_key_bytes']),
                'sk': bin2hstr(slave['private_key_bytes'])
            })
        
        with open('slaves.json', 'w') as f:
            address = src_falcon['address'] if src_falcon else bin2hstr(address_src_pk)
            json.dump([address, slave_info, tx.to_json()], f)
        click.echo('Successfully created slaves.json')
        click.echo('Move slaves.json file from current directory to the mining node inside ~/.qrl/')
    except Exception as e:
        click.echo("Unhandled error: {}".format(str(e)))
        quit(1)


@qrl.command(name='token_list')
@click.option('--owner', default='', prompt=True, help='source QRL address')
@click.pass_context
def token_list(ctx, owner):
    """
    Fetch the list of tokens owned by an address.
    """
    try:
        owner_address = parse_qaddress(owner)
    except Exception as e:
        click.echo("Error validating arguments: {}".format(e))
        quit(1)

    try:
        stub = ctx.obj.get_stub_public_api()
        address_state_req = qbit_pb2.GetAddressStateReq(address=owner_address)
        address_state_resp = stub.GetAddressState(address_state_req, timeout=CONNECTION_TIMEOUT)

        for token_hash in address_state_resp.state.tokens:
            get_object_req = qbit_pb2.GetObjectReq(query=bytes(hstr2bin(token_hash)))
            get_object_resp = stub.GetObject(get_object_req, timeout=CONNECTION_TIMEOUT)

            click.echo('Hash: %s' % (token_hash,))
            click.echo('Symbol: %s' % (get_object_resp.transaction.tx.token.symbol.decode(),))
            click.echo('Name: %s' % (get_object_resp.transaction.tx.token.name.decode(),))
            click.echo('Balance: %s' % (address_state_resp.state.tokens[token_hash],))

    except Exception as e:
        print("Error {}".format(str(e)))


@qrl.command(name='state')
@click.pass_context
def state(ctx):
    """
    Shows Information about a Node's State
    """
    stub = ctx.obj.get_stub_public_api()
    nodeStateResp = stub.GetNodeState(qbit_pb2.GetNodeStateReq())

    hstr_block_last_hash = bin2hstr(nodeStateResp.info.block_last_hash).encode()
    if ctx.obj.output_json:
        jsonMessage = MessageToDict(nodeStateResp)
        jsonMessage['info']['blockLastHash'] = hstr_block_last_hash
        click.echo(json.dumps(jsonMessage, indent=2, sort_keys=True))
    else:
        nodeStateResp.info.block_last_hash = hstr_block_last_hash
        click.echo(nodeStateResp)


def main():
    qrl()


if __name__ == '__main__':
    main()
