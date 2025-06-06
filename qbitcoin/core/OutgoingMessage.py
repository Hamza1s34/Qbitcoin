# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
from qbitcoin.core import config
from qbitcoin.core.misc import ntp


class OutgoingMessage:
    def __init__(self, priority, message):
        self.priority = priority
        self.timestamp = int(ntp.getTime())
        self.message = message

    def is_expired(self):
        return self.timestamp - ntp.getTime() > config.user.outgoing_message_expiry

    def __lt__(self, outgoing_message):
        return self.priority < outgoing_message.priority
