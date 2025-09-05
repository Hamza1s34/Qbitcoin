# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import faulthandler
import os

from mock import MagicMock
from twisted.internet import reactor
from pyqrllib.pyqrllib import hstr2bin, bin2hstr

from qbitcoin.core.AddressState import AddressState
from qbitcoin.core.Block import Block
from qbitcoin.core.ChainManager import ChainManager
from qbitcoin.core.GenesisBlock import GenesisBlock
from qbitcoin.core.misc import ntp, logger, set_logger
from qbitcoin.core.qbitnode import QbitcoinNode
from qbitcoin.services.services import start_services
from qbitcoin.core import config
from qbitcoin.core.State import State


def parse_arguments():
    parser = argparse.ArgumentParser(description='QRL node')
    parser.add_argument('--mining_thread_count', '-m', dest='mining_thread_count', type=int, required=False,
                        default=None, help="Number of threads for mining")
    parser.add_argument('--quiet', '-q', dest='quiet', action='store_true', required=False, default=False,
                        help="Avoid writing data to the console")
    parser.add_argument('--qrldir', '-d', dest='qrl_dir', default=config.user.qrl_dir,
                        help="Use a different directory for node data/configuration")
    parser.add_argument('--no-colors', dest='no_colors', action='store_true', default=False,
                        help="Disables color output")
    parser.add_argument("-l", "--loglevel", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the logging level")
    parser.add_argument('--network-type', dest='network_type', choices=['mainnet', 'testnet'],
                        default='mainnet', required=False, help="Runs QRL Testnet Node")
    parser.add_argument('--miningAddress', dest='mining_address', required=False,
                        help="Qbit Wallet address on which mining reward has to be credited.")
    parser.add_argument('--mockGetMeasurement', dest='measurement', required=False, type=int, default=-1,
                        help="Warning: Only for integration test, to mock get_measurement")
    parser.add_argument('--debug', dest='debug', action='store_true', default=False,
                        help="Enables fault handler")
    parser.add_argument('--mocknet', dest='mocknet', action='store_true', default=False,
                        help="Enables default mocknet settings")
    parser.add_argument('--dev-mode', dest='dev_mode', action='store_true', default=False,
                        help="Enables low difficulty development mode with custom mining address")
    # Staking arguments
    parser.add_argument('--stakingAddress', dest='staking_address', required=False,
                        help="Qbit Wallet address to start staking with")
    parser.add_argument('--loadDonorWallet', dest='donor_wallet', action='store_true',
                        help="Load donor wallet for staking rewards distribution (will prompt for password)")
    parser.add_argument('--miningstakingAddress', dest='mining_staking_address', required=False,
                        help="Qbit Wallet address to start both mining and staking simultaneously")
    parser.add_argument('--addDwallet', dest='add_donor_wallet', required=False,
                        help="Import a wallet file as donor wallet for staking rewards (provide path to wallet file)")
    return parser.parse_args()


def get_mining_address(mining_address: str):
    try:
        if not mining_address:
            mining_address = bytes(hstr2bin(config.user.mining_address[1:]))
        else:
            mining_address = bytes(hstr2bin(mining_address[1:]))

        if not AddressState.address_is_valid(mining_address):
            raise ValueError('Mining Address Validation Failed')

        return mining_address
    except Exception as e:
        logger.info('Failed Parsing Mining Address %s', e)

    return None


def main():
    args = parse_arguments()

    qrl_dir_post_fix = ''
    copy_files = []
    if args.network_type == 'testnet':
        # Hard Fork Block Height For Testnet
        config.dev.hard_fork_heights = list(config.dev.testnet_hard_fork_heights)
        # Hard Fork Block Height Disconnect Delay For Testnet
        config.dev.hard_fork_node_disconnect_delay = list(config.dev.testnet_hard_fork_node_disconnect_delay)
        qrl_dir_post_fix = '-testnet'
        package_directory = os.path.dirname(os.path.abspath(__file__))
        copy_files.append(os.path.join(package_directory, 'network/testnet/genesis.yml'))
        copy_files.append(os.path.join(package_directory, 'network/testnet/config.yml'))
        # Use lower difficulty for testnet for easier mining
        config.user.genesis_difficulty = 500

    logger.debug("=====================================================================================")
    logger.info("QRL Path: %s", args.qrl_dir)
    config.user.qrl_dir = os.path.expanduser(os.path.normpath(args.qrl_dir) + qrl_dir_post_fix)
    
    # Log the data directory path once at startup
    logger.info("Qbitcoin data directory: %s", config.user.qrl_dir)
    
    config.create_path(config.user.qrl_dir, copy_files)
    config.user.load_yaml(config.user.config_path)

    if args.mining_thread_count is None:
        args.mining_thread_count = config.user.mining_thread_count
    logger.debug("=====================================================================================")

    config.create_path(config.user.wallet_dir)
    mining_address = None
    ntp.setDrift()

    logger.info('Initializing chain..')
    persistent_state = State()

    if args.mocknet:
        args.debug = True
        config.user.mining_enabled = True
        config.user.mining_thread_count = 1
        config.user.mining_pause = 500
        config.dev.pbdata.block.block_timing_in_seconds = 1
        config.user.genesis_difficulty = 10  # Very easy for rapid testing

        # Use default mocknet mining address only if none provided
        if not args.mining_address:
            # Mocknet mining address
            # Q01050058bb3f8cb66fd90d0347478e5bdf3a475e82cfc5fe5dc276500ca21531e6edaf3d2d0f7e
            # Mocknet mining hexseed
            # 010500dd70f898c2cb4c11ce7fd85aa04554e41dcc46569871d189a3f48d84e2fbedbe176695e291e9b81e619b3625c624cde6
            args.mining_address = 'Q01050058bb3f8cb66fd90d0347478e5bdf3a475e82cfc5fe5dc276500ca21531e6edaf3d2d0f7e'

    if args.dev_mode:
        args.debug = True
        config.user.mining_enabled = True
        config.user.mining_thread_count = 2
        config.user.mining_pause = 100  # Slight pause to prevent 100% CPU usage
        config.dev.pbdata.block.block_timing_in_seconds = 60  # 1 minute target as requested
        config.user.genesis_difficulty = 100  # Low difficulty for development mining
        logger.info("Development mode enabled: Low difficulty mining with 1-minute block target")

    if args.debug:
        logger.warning("FAULT HANDLER ENABLED")
        faulthandler.enable()

    # Enable mining if mining address is provided
    if args.mining_address:
        config.user.mining_enabled = True
    
    # Handle combined mining and staking address
    if args.mining_staking_address:
        config.user.mining_enabled = True
        # Use the same address for both mining and staking
        if not args.mining_address:
            args.mining_address = args.mining_staking_address
        if not args.staking_address:
            args.staking_address = args.mining_staking_address
        logger.info('Combined mining and staking enabled for address: %s', args.mining_staking_address)

    if config.user.mining_enabled:
        mining_address = get_mining_address(args.mining_address)

        if not mining_address:
            logger.warning('Invalid Mining Credit Wallet Address')
            logger.warning('%s', args.mining_address)
            return False

    chain_manager = ChainManager(state=persistent_state)
    if args.measurement > -1:
        chain_manager.get_measurement = MagicMock(return_value=args.measurement)

    chain_manager.load(Block.deserialize(GenesisBlock().serialize()))

    qrlnode = QbitcoinNode(mining_address=mining_address)
    qrlnode.set_chain_manager(chain_manager)

    set_logger.set_logger(args, qrlnode.sync_state)

    #######
    # NOTE: Keep assigned to a variable or might get collected
    admin_service, grpc_service, mining_service, debug_service = start_services(qrlnode)

    qrlnode.start_listening()

    qrlnode.start_pow(args.mining_thread_count)

    logger.info('Qbitcoin blockchain  %s', config.dev.version)
    if config.user.mining_enabled:
        logger.info('Mining address %s using %s threads (0 = auto)', 'Q' + bin2hstr(mining_address), args.mining_thread_count)

    elif args.mining_address or args.mining_thread_count:
        logger.warning('Mining is not enabled but you sent some "mining related" param via CLI')

    # Initialize staking if requested
    if args.staking_address:
        try:
            staking_address = bytes(hstr2bin(args.staking_address[1:]))  # Remove Q prefix
            if qrlnode.start_staking(staking_address):
                logger.info('Staking started for address: %s', args.staking_address)
                
                # Try to auto-load donor wallet for mining+staking if available
                if args.mining_staking_address:
                    donor_wallets_dir = os.path.join(config.user.qrl_dir, 'donor_wallets')
                    if os.path.exists(donor_wallets_dir):
                        donor_files = [f for f in os.listdir(donor_wallets_dir) if f.endswith('_donor.json')]
                        if donor_files:
                            logger.info('Found donor wallet(s) for mining+staking. Attempting auto-load...')
                            # Try to auto-load unencrypted donor wallet
                            if qrlnode.staking_manager.auto_load_unencrypted_donor_wallet():
                                logger.info('Donor wallet auto-loaded successfully for reward distribution')
                            else:
                                logger.warning('Failed to auto-load donor wallet - rewards will not be distributed')
                                logger.info('Use --addDwallet to import your wallet for automatic loading')
                        else:
                            logger.info('No donor wallets found. Use --addDwallet to import your wallet for rewards')
                    else:
                        logger.info('No donor wallets directory. Use --addDwallet to import your wallet for rewards')
            else:
                logger.warning('Failed to start staking for address: %s', args.staking_address)
        except Exception as e:
            logger.error('Error starting staking: %s', str(e))
            
    # Load donor wallet if provided
    if args.donor_wallet:
        import getpass
        try:
            # For command line, we treat this as a password prompt
            logger.info('Donor wallet parameter provided. Please enter password to load donor wallet.')
            password = getpass.getpass("Enter donor wallet password: ")
            if qrlnode.load_donor_wallet(password):
                logger.info('Donor wallet loaded successfully')
            else:
                logger.warning('Failed to load donor wallet (wrong password or file not found)')
        except Exception as e:
            logger.error('Error loading donor wallet: %s', str(e))

    # Import new donor wallet if provided
    if args.add_donor_wallet:
        import getpass
        import json
        from qbitcoin.core.DonorWalletManager import DonorWalletManager
        
        try:
            wallet_path = args.add_donor_wallet
            if not os.path.exists(wallet_path):
                logger.error('Wallet file not found: %s', wallet_path)
                return False
            else:
                logger.info('Importing donor wallet from: %s', wallet_path)
                
                # Check if file is encrypted or not
                try:
                    with open(wallet_path, 'r') as f:
                        wallet_data = json.load(f)
                    
                    # Check wallet file structure
                    if not isinstance(wallet_data, dict):
                        logger.error('Invalid wallet file structure: must be a JSON object')
                        return False
                    elif 'encrypted' in wallet_data and wallet_data.get('encrypted'):
                        # Encrypted wallet - need password to decrypt and save unencrypted
                        logger.info('Wallet is encrypted. Please enter password to decrypt and save unencrypted.')
                        password = getpass.getpass("Enter wallet password: ")
                        
                        donor_manager = DonorWalletManager()
                        if donor_manager.import_encrypted_wallet_as_unencrypted(wallet_path, password):
                            logger.info('Encrypted donor wallet decrypted and saved unencrypted for automatic loading')
                            return True
                        else:
                            logger.error('Failed to import encrypted donor wallet (wrong password or invalid file)')
                            return False
                    elif ('address' in wallet_data and ('pk' in wallet_data or 'private_key_hex' in wallet_data or 'private_key' in wallet_data)) or ('addresses' in wallet_data):
                        # Unencrypted wallet - save as-is unencrypted for automatic loading
                        logger.info('Wallet is unencrypted. Importing directly without encryption...')
                        
                        donor_manager = DonorWalletManager()
                        if donor_manager.import_unencrypted_wallet_direct(wallet_path):
                            logger.info('Unencrypted donor wallet imported and saved for automatic loading')
                            return True
                        else:
                            logger.error('Failed to import unencrypted donor wallet')
                            return False
                    else:
                        logger.error('Invalid wallet file structure: missing required fields')
                        logger.error('Expected: (address + pk/private_key_hex/private_key) or (addresses)')
                        logger.error('Found keys: %s', list(wallet_data.keys()))
                        return False
                        
                except json.JSONDecodeError:
                    logger.error('Invalid wallet file: not a valid JSON file')
                    return False
                except Exception as e:
                    logger.error('Error reading wallet file: %s', str(e))
                    return False
                    
        except Exception as e:
            logger.error('Error importing donor wallet: %s', str(e))
            return False

    reactor.run()

def run():
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Keyboard Interrupt received, shutting down...')
        reactor.stop()
    except Exception as e:
        logger.exception('An error occurred: %s' % str(e))
        reactor.stop()
if __name__ == '__main__':
    run()