# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
import shutil
import decimal
from os.path import expanduser
from pyqrllib.pyqrllib import hstr2bin
from qbitcoin import __version__ as version
from qbitcoin.generated import qbit_pb2

import os

import yaml
from math import ceil, log


class UserConfig(object):
    __instance = None

    def __init__(self, ignore_check=False):
        # TODO: Move to metaclass in Python 3
        if not ignore_check and UserConfig.__instance is not None:
            raise Exception("UserConfig can only be instantiated once")

        UserConfig.__instance = self

        self.genesis_prev_headerhash = b'The sleeper must awaken'
        self.genesis_timestamp = 1748476800  # Updated to current time (May 29, 2025)
        self.genesis_difficulty = 5000 

        # Default configuration
        self.mining_enabled = False
        self.mining_address = ''
        self.mining_thread_count = 0  # 0 to auto detect thread count based on CPU/GPU number of processors
        self.mining_pause = 0  # this will force a sleep (ms) while mining to reduce cpu usage. Only for mocknet

        # Ephemeral Configuration
        self.accept_ephemeral = True

        # PEER Configuration
        self.max_redundant_connections = 5  # Number of connections allowed from nodes having same IP
        self.enable_peer_discovery = True  # Allows to discover new peers from the connected peers

        self.peer_list = ["134.122.79.166",
                          "220.158.73.254"]

        self.p2p_local_port = 19000  # Locally binded port at which node will listen for connection
        self.p2p_public_port = 19000  # Public port forwarding connections to server

        self.peer_rate_limit = 500  # Max Number of messages per minute per peer
        self.p2p_q_size = 10000
        self.outgoing_message_expiry = 90  # Outgoing message expires after 90 seconds

        self.ntp_servers = ['pool.ntp.org', 'ntp.ubuntu.com']
        self.ntp_refresh = 12 * 60 * 60  # 12 hours
        self.ntp_request_timeout = 10  # 10 seconds ntp timeout
        self.ban_minutes = 20  # Allows to ban a peer's IP who is breaking protocol

        self.monitor_connections_interval = 30  # Monitor connection every 30 seconds
        self.max_peers_limit = 100  # Number of allowed peers
        self.chain_state_timeout = 180
        self.chain_state_broadcast_period = 30
        # must be less than ping_timeout

        self.transaction_minimum_fee = int(0.0001 * (10 ** 9))  # 0.0001 Qbitcoin in quarks
        self.transaction_pool_size = 25000
        self.pending_transaction_pool_size = 75000
        # 1% of the pending_transaction_pool will be reserved for moving stale txn
        self.pending_transaction_pool_reserve = int(self.pending_transaction_pool_size * 0.01)
        self.stale_transaction_threshold = 15  # 15 Blocks

        # Store data in user's application data directory (outside project)
        self._qrl_dir = self._get_default_data_directory()

        # ======================================
        #        ADMIN API CONFIGURATION
        # ======================================
        self.admin_api_enabled = False
        self.admin_api_host = "127.0.0.1"
        self.admin_api_port = 19008
        self.admin_api_threads = 1
        self.admin_api_max_concurrent_rpc = 100

        # ======================================
        #        PUBLIC API CONFIGURATION
        # ======================================
        self.public_api_enabled = True
        self.public_api_host = "0.0.0.0" # only if you want to expose the API to the public 
        self.public_api_port = 19009
        self.public_api_threads = 1
        self.public_api_max_concurrent_rpc = 100

        # ======================================
        #        MINING API CONFIGURATION
        # ======================================
        self.mining_api_enabled = False
        self.mining_api_host = "127.0.0.1"
        self.mining_api_port = 19007
        self.mining_api_threads = 1
        self.mining_api_max_concurrent_rpc = 100

        # ======================================
        #        DEBUG API CONFIGURATION
        # ======================================
        self.debug_api_enabled = False
        self.debug_api_host = "127.0.0.1"
        self.debug_api_port = 52134
        self.debug_api_threads = 1
        self.debug_api_max_concurrent_rpc = 100

        # ======================================
        #        GRPC PROXY CONFIGURATION
        # ======================================
        self.grpc_proxy_host = "127.0.0.1"
        self.grpc_proxy_port = 18090

        # ======================================
        #      WALLET DAEMON CONFIGURATION
        # ======================================
        self.public_api_server = "127.0.0.1:19009"
        self.wallet_daemon_host = "127.0.0.1"
        self.wallet_daemon_port = 18091
        self.number_of_slaves = 3

        # ======================================
        #        WALLET API CONFIGURATION
        # ======================================
        self.wallet_api_host = "0.0.0.0" #same as public api 
        self.wallet_api_port = 19010
        self.wallet_api_threads = 1
        self.wallet_api_max_concurrent_rpc = 100

        # WARNING! loading should be the last line.. any new setting after this will not be updated by the config file
        self.load_yaml(self.config_path)
        # WARNING! loading should be the last line.. any new setting after this will not be updated by the config file

    def _get_default_data_directory(self):
        """Get the default data directory based on the operating system"""
        import platform
        
        system = platform.system()
        home = expanduser("~")
        
        if system == "Windows":
            # Windows: %APPDATA%\Qbitcoin
            app_data = os.environ.get('APPDATA', os.path.join(home, 'AppData', 'Roaming'))
            return os.path.join(app_data, 'Qbitcoin')
        elif system == "Darwin":  # macOS
            # macOS: ~/Library/Application Support/Qbitcoin
            return os.path.join(home, 'Library', 'Application Support', 'Qbitcoin')
        else:  # Linux and other Unix-like systems
            # Linux: ~/.local/share/qbitcoin or ~/.qbitcoin (fallback)
            xdg_data_home = os.environ.get('XDG_DATA_HOME', os.path.join(home, '.local', 'share'))
            return os.path.join(xdg_data_home, 'qbitcoin')

    @property
    def qrl_dir(self):
        return self._qrl_dir

    @qrl_dir.setter
    def qrl_dir(self, new_qrl_dir):
        self._qrl_dir = new_qrl_dir
        self.load_yaml(self.config_path)

    @property
    def wallet_dir(self):
        return expanduser(self.qrl_dir)

    @property
    def data_dir(self):
        return expanduser(os.path.join(self.qrl_dir, "data"))

    @property
    def config_path(self):
        return expanduser(os.path.join(self.qrl_dir, "config.yml"))

    @property
    def log_path(self):
        return expanduser(os.path.join(self.qrl_dir, "qrl.log"))

    @property
    def walletd_log_path(self):
        return expanduser(os.path.join(self.qrl_dir, "walletd.log"))

    @property
    def mining_pool_payment_wallet_path(self):
        return expanduser(os.path.join(self.qrl_dir, 'payment_slaves.json'))

    @staticmethod
    def getInstance():
        if UserConfig.__instance is None:
            return UserConfig()
        return UserConfig.__instance

    def load_yaml(self, file_path):
        """
        Overrides default configuration using a yaml file
        :param file_path: The path to the configuration file
        """
        if os.path.isfile(file_path):
            with open(file_path) as f:
                dataMap = yaml.safe_load(f)
                if dataMap is not None:
                    if 'genesis_prev_headerhash' in dataMap:
                        dataMap['genesis_prev_headerhash'] = dataMap['genesis_prev_headerhash'].encode()
                    self.__dict__.update(**dataMap)


def create_path(path, copy_files=None):
    """Create directory path if it doesn't exist"""
    tmp_path = os.path.join(path)
    if os.path.isdir(tmp_path):
        return
    
    try:
        os.makedirs(tmp_path, exist_ok=True)
        # Import logger here to avoid circular imports
        from qbitcoin.core.misc import logger
        logger.info("Created data directory: %s", tmp_path)
    except OSError as e:
        # Import logger here to avoid circular imports
        from qbitcoin.core.misc import logger
        logger.error("Failed to create data directory %s: %s", tmp_path, str(e))
        raise
    
    if not copy_files:
        return
    for file in copy_files:
        shutil.copy(file, tmp_path)


class DevConfig(object):
    __instance = None

    def __init__(self, pbdata, ignore_check=False, ignore_singleton=False):
        super(DevConfig, self).__init__()
        # TODO: Move to metaclass in Python 3
        if not ignore_check and DevConfig.__instance is not None:
            raise Exception("DevConfig can only be instantiated once")

        if not ignore_singleton:
            DevConfig.__instance = self

        self._data = pbdata

        self.version = version + ' python'

        ################################################################
        # Warning: Don't change following configuration.               #
        #          For Qbitcoin  Developers only                             #
        ################################################################

        self.block_lead_timestamp = 30
        self.block_max_drift = 15
        self.max_future_blocks_length = 256
        self.max_margin_block_number = 32
        self.min_margin_block_number = 7

        self.public_ip = None
        self.cache_frequency = 1000

        self.message_q_size = 300
        self.message_receipt_timeout = 10  # request timeout for full message
        self.message_buffer_size = 64 * 1024 * 1024  # 64 MB

        self.timestamp_error = 5  # Error in second

        self.blocks_per_epoch = 100
         
         

         

        self.default_nonce = 0
        self.default_account_balance = 0 * (10 ** 9)
        self.hash_buffer_size = 4
        self.minimum_minting_delay = 45  # Minimum delay in second before a block is being created

        self.tx_extra_overhead = 15  # 15 bytes
        self.coinbase_address = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        # Directories and files
        self.db_name = 'state'
        self.peers_filename = 'known_peers.json'
        self.chain_file_directory = 'data'
        self.wallet_dat_filename = 'wallet.wallet'
        self.slave_dat_filename = 'slave.qrl'
        self.banned_peers_filename = 'banned_peers.qrl'

        self.trust_min_msgcount = 10
        self.trust_min_conntime = 10

        self.supplied_coins = 20000000 * (10 ** 9)  # 20 million QBCfor genesis

        # ======================================
        #      STATE VERSION
        # ======================================
        # Max number of data to be stored per key
        self._state_version = 3

        # ======================================
        #      STATE PAGINATION CONTROLLER
        # ======================================
        # Max number of data to be stored per key
        self._data_per_page = 10000

        # ======================================
        #            P2P SETTINGS
        # ======================================
        self.max_receivable_bytes = 10 * 1024 * 1024  # 10 MB [Temporary Restriction]
        self.reserved_quota = 1024  # 1 KB
        self.max_bytes_out = self.max_receivable_bytes - self.reserved_quota
        self.sync_delay_mining = 60  # Delay mining by 60 seconds while syncing blocks to mainchain

        # ======================================
        #            API SETTINGS
        # ======================================
        self.block_timeseries_size = 1440

        # ======================================
        # SHOR PER QUANTA / MAX ALLOWED DECIMALS
        # ======================================
        self.quark_per_qbitcoin = decimal.Decimal(10 ** 9)

        # ======================================
        # # FOUNDATION MULTI-SIG ADDRESSES
        # # ======================================
        # self.percentage = 100  # multiplier for foundation_address_threshold_percentage to keep it an integer
        # self.foundation_multi_sig_addresses = [b'\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        #                                        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        #                                        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        #                                        ]

        # ======================================
        # HARD FORK HEIGHTS LIST
        # ======================================
        self.hard_fork_heights = [942375, 1938000, 2078800]
        self.hard_fork_node_disconnect_delay = [0, 0, 2880]
        self.testnet_hard_fork_heights = [0, 0, 0]
        self.testnet_hard_fork_node_disconnect_delay = [0, 0, 0]

        # ======================================
        # PROPOSAL CONFIG
        # ======================================
        self.proposal_unit_percentage = 100
        self.banned_address = [bytes(hstr2bin('010600fcd0db869d2e1b17b452bdf9848f6fe8c74ee5b8f935408cc558c601fb69eb553fa916a1'))]

    @property
    def pbdata(self):
        return self._data

    @property
    def state_version(self):
        return self._state_version

    @property
    def prev_state_key(self):
        return self._data.prev_state_key

    @property
    def current_state_key(self):
        return self._data.current_state_key

    @property
    def activation_header_hash(self):
        return self._data.activation_header_hash

    @property
    def activation_block_number(self):
        return self._data.activation_block_number

    @property
    def data_per_page(self):
        return self._data_per_page

    #@property
   # def ots_tracking_per_page(self):
       # return self._ots_tracking_per_page

    #@property
    #def ots_bitfield_size(self):
        #return self._ots_bitfield_size

    @property
    def reorg_limit(self):
        return self.pbdata.chain.reorg_limit

    @property
    def max_coin_supply(self):
        return decimal.Decimal(self.pbdata.chain.max_coin_supply)

    @property
    def complete_emission_time_span_in_years(self):
        return self.pbdata.chain.complete_emission_time_span_in_years

    @property
    def coin_remaining_at_genesis(self):
        # For 30M max supply with 20M allocated at genesis, 10M remains for mining rewards
        return decimal.Decimal(self.pbdata.chain.max_coin_supply - 20000000)

    @property
    def mining_nonce_offset(self):
        return self.pbdata.block.mining_nonce_offset

    @property
    def extra_nonce_offset(self):
        return self.pbdata.block.extra_nonce_offset

    @property
    def mining_blob_size_in_bytes(self):
        return self.pbdata.block.mining_blob_size_in_bytes

    @property
    def block_timing_in_seconds(self):
        return self.pbdata.block.block_timing_in_seconds

    @property
    def number_of_blocks_to_analyze(self):
        return self.pbdata.block.block_size_controller.number_of_blocks_analyze

    @property
    def size_multiplier(self):
        return self.pbdata.block.block_size_controller.size_multiplier / 100

    @property
    def block_min_size_limit_in_bytes(self):
        return self.pbdata.block.block_size_controller.block_min_size_limit_in_bytes

    @property
    def transaction_multi_output_limit(self):
        return self.pbdata.transaction.multi_output_limit

    # @property
    # def foundation_address_threshold_percentage(self):
    #     return self.pbdata.transaction.foundation_multi_sig.threshold_percentage

    @property
    def message_max_length(self):
        return self.pbdata.transaction.message.max_length

    @property
    def slave_pk_max_length(self):
        return self.pbdata.transaction.slave.slave_pk_max_length

    @property
    def max_token_symbol_length(self):
        return self.pbdata.transaction.token.symbol_max_length

    @property
    def max_token_name_length(self):
        return self.pbdata.transaction.token.name_max_length

    @property
    def lattice_pk1_max_length(self):
        return self.pbdata.transaction.lattice.pk1_max_length

    @property
    def lattice_pk2_max_length(self):
        return self.pbdata.transaction.lattice.pk2_max_length

    @property
    def lattice_pk3_max_length(self):
        return self.pbdata.transaction.lattice.pk3_max_length

    @property
    def proposal_threshold_per(self):
        return self.pbdata.transaction.proposal.threshold_per

    @property
    def default_proposal_options(self):
        return self.pbdata.transaction.proposal.default_options

    @property
    def description_max_length(self):
        return self.pbdata.transaction.proposal.description_max_length

    @property
    def options_max_number(self):
        return self.pbdata.transaction.proposal.options_max_number

    @property
    def option_max_text_length(self):
        return self.pbdata.transaction.proposal.option_max_text_length

    @property
    def proposal_config_activation_delay(self):
        return self.pbdata.transaction.proposal.proposal_config_activation_delay

    @property
    def N_measurement(self):
        return self.pbdata.pow.N_measurement

    @property
    def kp(self):
        return self.pbdata.pow.kp

    @staticmethod
    def getInstance(prev_state_key,
                    current_state_key: bytes,
                    current_block_header_hash: bytes,
                    current_block_number: int):
        if DevConfig.__instance is None:
            return DevConfig.create(prev_state_key,
                                    current_state_key,
                                    current_block_header_hash,
                                    current_block_number)
        return DevConfig.__instance

    @staticmethod
    def get_state_key(headerhash: bytes):
        return b'dev_config_' + headerhash

    @staticmethod
    def create(prev_state_key,
               current_state_key: bytes,
               current_block_header_hash: bytes,
               current_block_number: int,
               ignore_check=False,
               ignore_singleton=False):
        chain = qbit_pb2.DevConfig.Chain(reorg_limit=300,
                                        max_coin_supply=30000000,
                                        complete_emission_time_span_in_years=4)  # Changed to 4 years for halving
        block_size_controller = qbit_pb2.DevConfig.Block.BlockSizeController(number_of_blocks_analyze=10,
                                                                            size_multiplier=110,  # 1.1
                                                                            block_min_size_limit_in_bytes=1024 * 1024)
        block = qbit_pb2.DevConfig.Block(mining_nonce_offset=39,
                                        extra_nonce_offset=43,
                                        mining_blob_size_in_bytes=76,
                                        block_timing_in_seconds=60,  # 1 minute blocks
                                        block_size_controller=block_size_controller)

        message = qbit_pb2.DevConfig.Transaction.Message(max_length=80)

        slave = qbit_pb2.DevConfig.Transaction.Slave(slave_pk_max_length=67)

        token = qbit_pb2.DevConfig.Transaction.Token(symbol_max_length=10,
                                                    name_max_length=30)

        lattice = qbit_pb2.DevConfig.Transaction.Lattice(pk1_max_length=1088,
                                                        pk2_max_length=1472,
                                                        pk3_max_length=65)

        foundation_multi_sig = qbit_pb2.DevConfig.Transaction.FoundationMultiSig(threshold_percentage=10)

        # proposal_config_activation_delay should not be less than reorg_limit
        proposal = qbit_pb2.DevConfig.Transaction.Proposal(threshold_per=51,
                                                          default_options=["YES", "NO", "ABSTAIN"],
                                                          description_max_length=400,
                                                          options_max_number=100,
                                                          option_max_text_length=30,
                                                          proposal_config_activation_delay=10)

        transaction = qbit_pb2.DevConfig.Transaction(multi_output_limit=100,
                                                    message=message,
                                                    slave=slave,
                                                    token=token,
                                                    lattice=lattice,
                                                    foundation_multi_sig=foundation_multi_sig,
                                                    proposal=proposal)

        dev_config = qbit_pb2.DevConfig(chain=chain,
                                       block=block,
                                       transaction=transaction,
                                       pow=qbit_pb2.DevConfig.POW(N_measurement=30, kp=5))

        if prev_state_key is not None:
            dev_config.prev_state_key = prev_state_key
        dev_config.current_state_key = current_state_key

        dev_config.activation_header_hash = current_block_header_hash
        dev_config.activation_block_number = current_block_number

        return DevConfig(dev_config,
                         ignore_check,
                         ignore_singleton)

    def serialize(self) -> str:
        return self._data.SerializeToString()

    @staticmethod
    def deserialize(data):
        pbdata = qbit_pb2.DevConfig()
        pbdata.ParseFromString(bytes(data))
        dev_config = DevConfig(pbdata)
        return dev_config

    def update_from_pbdata(self, pbdata):
        self._data = pbdata


# Hard coded Genesis Header Hash, must be updated if any change is made to genesis block
# Updated Genesis Hash: b2a7aa80ddfa84ac117c5822bd4046160585238f850ffe8265f3ba1d26616264 (July 5, 2025)
genesis_header_hash = bytes(hstr2bin('b2a7aa80ddfa84ac117c5822bd4046160585238f850ffe8265f3ba1d26616264'))
dev = DevConfig.getInstance(None,
                            DevConfig.get_state_key(genesis_header_hash),
                            genesis_header_hash,
                            0)
user = UserConfig.getInstance()
