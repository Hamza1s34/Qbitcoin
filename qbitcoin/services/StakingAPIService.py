# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from pyqrllib.pyqrllib import hstr2bin, bin2hstr

from qbitcoin.core.misc import logger
from qbitcoin.services.BaseService import BaseService
from qbitcoin.services.grpcHelper import GrpcExceptionWrapper
from qbitcoin.generated import qbit_pb2


class StakingAPIService(BaseService):
    def __init__(self, qbitnode):
        super().__init__(qbitnode)

    @GrpcExceptionWrapper(qbit_pb2.GetStakingInfoResp)
    def GetStakingInfo(self, request: qbit_pb2.GetStakingInfoReq, context) -> qbit_pb2.GetStakingInfoResp:
        """Get current staking information"""
        logger.debug("[StakingAPI] GetStakingInfo")
        answer = qbit_pb2.GetStakingInfoResp()
        
        try:
            staking_info = self.qbitnode.get_staking_info()
            
            answer.total_stakers = staking_info.get('total_stakers', 0)
            answer.active_stakers = staking_info.get('active_stakers', 0)
            answer.total_stake = staking_info.get('total_stake', 0)
            answer.donor_wallet = staking_info.get('donor_wallet', '')
            answer.last_reward_block = staking_info.get('last_reward_block', 0)
            answer.staking_enabled = staking_info.get('staking_enabled', False)
            
        except Exception as e:
            logger.error("GetStakingInfo failed: %s", str(e))
            answer.total_stakers = 0
            answer.active_stakers = 0
            answer.total_stake = 0
            answer.donor_wallet = ''
            answer.last_reward_block = 0
            answer.staking_enabled = False
            
        return answer

    @GrpcExceptionWrapper(qbit_pb2.GetStakersResp)
    def GetStakers(self, request: qbit_pb2.GetStakersReq, context) -> qbit_pb2.GetStakersResp:
        """Get list of active stakers"""
        logger.debug("[StakingAPI] GetStakers")
        answer = qbit_pb2.GetStakersResp()
        
        try:
            stakers = self.qbitnode.get_staker_list()
            
            for address_str, stake_info in stakers.items():
                staker_info = qbit_pb2.StakerInfo()
                staker_info.address = address_str
                staker_info.balance = stake_info.get('balance', 0)
                staker_info.stake_start_time = int(stake_info.get('stake_start_time', 0))
                staker_info.last_seen_time = int(stake_info.get('last_seen_time', 0))
                staker_info.is_online = stake_info.get('is_online', False)
                
                answer.stakers.append(staker_info)
                
        except Exception as e:
            logger.error("GetStakers failed: %s", str(e))
            
        return answer

    @GrpcExceptionWrapper(qbit_pb2.StartStakingResp)
    def StartStaking(self, request: qbit_pb2.StartStakingReq, context) -> qbit_pb2.StartStakingResp:
        """Start staking for an address"""
        logger.debug("[StakingAPI] StartStaking")
        answer = qbit_pb2.StartStakingResp()
        
        try:
            # Validate address format
            if not request.address.startswith('Q'):
                answer.success = False
                answer.error_message = "Address must start with 'Q'"
                return answer
                
            # Convert address
            address_bytes = bytes(hstr2bin(request.address[1:]))
            
            # Start staking
            success = self.qbitnode.start_staking(address_bytes)
            
            answer.success = success
            if not success:
                answer.error_message = "Failed to start staking. Check balance and requirements."
            else:
                answer.error_message = ""
                
        except Exception as e:
            logger.error("StartStaking failed: %s", str(e))
            answer.success = False
            answer.error_message = str(e)
            
        return answer

    @GrpcExceptionWrapper(qbit_pb2.StopStakingResp)
    def StopStaking(self, request: qbit_pb2.StopStakingReq, context) -> qbit_pb2.StopStakingResp:
        """Stop staking for an address"""
        logger.debug("[StakingAPI] StopStaking")
        answer = qbit_pb2.StopStakingResp()
        
        try:
            # Validate address format
            if not request.address.startswith('Q'):
                answer.success = False
                answer.error_message = "Address must start with 'Q'"
                return answer
                
            # Convert address
            address_bytes = bytes(hstr2bin(request.address[1:]))
            
            # Stop staking
            success = self.qbitnode.stop_staking(address_bytes)
            
            answer.success = success
            if not success:
                answer.error_message = "Failed to stop staking. Address may not be staking."
            else:
                answer.error_message = ""
                
        except Exception as e:
            logger.error("StopStaking failed: %s", str(e))
            answer.success = False
            answer.error_message = str(e)
            
        return answer

    @GrpcExceptionWrapper(qbit_pb2.SetDonorWalletResp)
    def SetDonorWallet(self, request: qbit_pb2.SetDonorWalletReq, context) -> qbit_pb2.SetDonorWalletResp:
        """Set donor wallet for staking rewards"""
        logger.debug("[StakingAPI] SetDonorWallet")
        answer = qbit_pb2.SetDonorWalletResp()
        
        try:
            # Validate address format
            if not request.address.startswith('Q'):
                answer.success = False
                answer.error_message = "Address must start with 'Q'"
                return answer
                
            # Convert address
            address_bytes = bytes(hstr2bin(request.address[1:]))
            
            # Set donor wallet
            success = self.qbitnode.set_donor_wallet(address_bytes)
            
            answer.success = success
            if not success:
                answer.error_message = "Failed to set donor wallet."
            else:
                answer.error_message = ""
                
        except Exception as e:
            logger.error("SetDonorWallet failed: %s", str(e))
            answer.success = False
            answer.error_message = str(e)
            
        return answer

    @GrpcExceptionWrapper(qbit_pb2.StakerHeartbeatResp)
    def StakerHeartbeat(self, request: qbit_pb2.StakerHeartbeatReq, context) -> qbit_pb2.StakerHeartbeatResp:
        """Update staker heartbeat to maintain online status"""
        logger.debug("[StakingAPI] StakerHeartbeat")
        answer = qbit_pb2.StakerHeartbeatResp()
        
        try:
            # Validate address format
            if not request.address.startswith('Q'):
                answer.success = False
                answer.error_message = "Address must start with 'Q'"
                return answer
                
            # Convert address
            address_bytes = bytes(hstr2bin(request.address[1:]))
            
            # Update heartbeat
            self.qbitnode.update_staker_heartbeat(address_bytes)
            
            answer.success = True
            answer.error_message = ""
                
        except Exception as e:
            logger.error("StakerHeartbeat failed: %s", str(e))
            answer.success = False
            answer.error_message = str(e)
            
        return answer
