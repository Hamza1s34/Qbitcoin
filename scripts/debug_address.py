#!/usr/bin/env python3
import base64

falcon_address = 'Ac8oK2beuuYpbNQBfIrqmDpwfqFOYitCXA=='
decoded = base64.b64decode(falcon_address)
print(f'Falcon address length: {len(decoded)} bytes')
print(f'Falcon address hex: {decoded.hex()}')
print(f'First byte: 0x{decoded[0]:02x}')

coinbase = base64.b64decode('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=')
print(f'Coinbase length: {len(coinbase)} bytes') 
print(f'Coinbase hex: {coinbase.hex()}')
