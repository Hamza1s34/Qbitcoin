from pyqrllib.pyqrllib import bin2hstr
from pyqryptonight.pyqryptonight import UInt256ToString

from qbitcoin.core.misc import logger
from qbitcoin.core.Block import Block
from qbitcoin.core.p2p.p2pObserver import P2PBaseObserver
from qbitcoin.generated import qbitlegacy_pb2, qbit_pb2


class P2PChainManager(P2PBaseObserver):
    def __init__(self):
        super().__init__()

    def new_channel(self, channel):
        channel.register(qbitlegacy_pb2.LegacyMessage.BK, self.handle_block)
        channel.register(qbitlegacy_pb2.LegacyMessage.FB, self.handle_fetch_block)
        channel.register(qbitlegacy_pb2.LegacyMessage.PB, self.handle_push_block)
        channel.register(qbitlegacy_pb2.LegacyMessage.BH, self.handle_block_height)
        channel.register(qbitlegacy_pb2.LegacyMessage.HEADERHASHES, self.handle_node_headerhash)
        # Register staker message handler using PL (peer list) message type for staker announcements
        channel.register(qbitlegacy_pb2.LegacyMessage.PL, self.handle_peer_message)

    def handle_fetch_block(self, source, message: qbitlegacy_pb2.LegacyMessage):  # Fetch Request for block
        """
        Fetch Block
        Sends the request for the block.
        :return:
        """
        P2PBaseObserver._validate_message(message, qbitlegacy_pb2.LegacyMessage.FB)

        block_number = message.fbData.index

        logger.info(' Request for %s by %s', block_number, source.peer)
        if 0 < block_number <= source.factory.chain_height:
            block = source.factory.get_block_by_number(block_number)
            msg = qbitlegacy_pb2.LegacyMessage(func_name=qbitlegacy_pb2.LegacyMessage.PB,
                                              pbData=qbitlegacy_pb2.PBData(block=block.pbdata))
            source.send(msg)

    def handle_push_block(self, source, message: qbitlegacy_pb2.LegacyMessage):
        """
        Push Block
        This function processes requested blocks received while syncing.
        Block received under this function are directly added to the main
        chain i.e. chain.blockchain
        It is expected to receive only one block for a given blocknumber.
        :return:
        """
        # FIXME: Later rename
        P2PBaseObserver._validate_message(message, qbitlegacy_pb2.LegacyMessage.PB)
        if message.pbData is None:
            return

        try:
            block = Block(message.pbData.block)
            source.factory.block_received(source, block)

        except Exception as e:
            logger.error('block rejected - unable to decode serialised data %s', source.peer)
            logger.exception(e)

    def handle_block(self, source, message: qbitlegacy_pb2.LegacyMessage):  # block received
        """
        Block
        This function processes any new block received.
        :return:
        """
        P2PBaseObserver._validate_message(message, qbitlegacy_pb2.LegacyMessage.BK)
        try:
            block = Block(message.block)
        except Exception as e:
            logger.error('block rejected - unable to decode serialised data %s', source.peer)
            logger.exception(e)
            return

        logger.info('>>>Received block from %s %s %s',
                    source.peer.full_address,
                    block.block_number,
                    bin2hstr(block.headerhash))

        if not source.factory.master_mr.isRequested(block.headerhash, source, block):
            return

        source.factory.pow.pre_block_logic(block)  # FIXME: Ignores return value
        source.factory.master_mr.register(qbitlegacy_pb2.LegacyMessage.BK, block.headerhash, message.block)

    def handle_block_height(self, source, message: qbitlegacy_pb2.LegacyMessage):
        """
        Sends / Receives Blockheight
        :param source:
        :param message:
        :return:
        """
        if message.bhData.block_number == 0:
            block = source.factory.last_block
            cumulative_difficulty = source.factory.get_cumulative_difficulty()
            if block.block_number == 0:
                return
            bhdata = qbit_pb2.BlockHeightData(block_number=block.block_number,
                                             block_headerhash=block.headerhash,
                                             cumulative_difficulty=bytes(cumulative_difficulty))
            msg = qbitlegacy_pb2.LegacyMessage(func_name=qbitlegacy_pb2.LegacyMessage.BH,
                                              bhData=bhdata)
            source.send(msg)
            return

        try:
            UInt256ToString(message.bhData.cumulative_difficulty)
        except ValueError:
            logger.warning('Invalid Block Height Data')
            source.loseConnection()
            return

        source.factory.update_peer_blockheight(source.peer.full_address,
                                               message.bhData.block_number,
                                               message.bhData.block_headerhash,
                                               message.bhData.cumulative_difficulty)

    def handle_node_headerhash(self, source, message: qbitlegacy_pb2.LegacyMessage):
        """
        Sends/Receives NodeHeaderHashes
        :param source:
        :param message:
        :return:
        """

        if len(message.nodeHeaderHash.headerhashes) == 0:
            node_headerhash = source.factory.get_headerhashes(message.nodeHeaderHash.block_number)
            msg = qbitlegacy_pb2.LegacyMessage(func_name=qbitlegacy_pb2.LegacyMessage.HEADERHASHES,
                                              nodeHeaderHash=node_headerhash)
            source.send(msg)
        else:
            source.factory.compare_and_sync(source, message.nodeHeaderHash)

    def handle_peer_message(self, source, message: qbitlegacy_pb2.LegacyMessage):
        """
        Handle peer messages which can include staker announcements
        :param source: Peer connection that sent the message
        :param message: Legacy message containing peer or staker data
        :return:
        """
        try:
            P2PBaseObserver._validate_message(message, qbitlegacy_pb2.LegacyMessage.PL)
            
            # Check if this PL message contains staker data by looking at peer_ips
            if message.plData and message.plData.peer_ips:
                for peer_ip_data in message.plData.peer_ips:
                    # Check if this is a staker announcement (starts with special prefix)
                    if peer_ip_data.startswith("STAKER:"):
                        try:
                            import json
                            # Extract staker JSON data after the "STAKER:" prefix
                            staker_json = peer_ip_data[7:]  # Remove "STAKER:" prefix
                            staker_data = json.loads(staker_json)
                            
                            # Verify this is a valid staker message
                            if staker_data.get('type') == 'staker_update':
                                # Get peer IP from the source connection 
                                peer_ip = source.transport.getPeer().host
                                
                                # Pass to staking manager if available
                                if hasattr(source.factory, '_qrl_node') and hasattr(source.factory._qrl_node, 'staking_manager'):
                                    logger.info("Received staker message from peer %s: %s %s", 
                                              peer_ip, staker_data.get('action', 'unknown'), staker_data.get('address', 'unknown'))
                                    source.factory._qrl_node.staking_manager.handle_peer_staker_message(staker_data, peer_ip)
                                else:
                                    logger.debug("No staking manager available to handle peer staker message")
                                    
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.debug("Invalid staker data in peer message: %s", str(e))
                            
        except Exception as e:
            logger.error("Error handling peer message from %s: %s", source.peer, str(e))
