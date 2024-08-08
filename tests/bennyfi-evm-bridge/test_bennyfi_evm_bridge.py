#!/usr/bin/env python3

import json
import logging
import pytest
from eth_account import Account

# from w3multicall.multicall import W3Multicall

from pathlib import Path
from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3

from tevmc.utils import to_wei


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000

def test_all(tevmc_local):
    tevmc = tevmc_local
    tevmc.logger.setLevel(logging.DEBUG)
    local_w3 = open_web3(tevmc)

    # Test connection
    assert local_w3.is_connected()

    bridge_z_account = 'benybridge'
    tevmc.cleos.deploy_contract_from_path(
            bridge_z_account,
            Path('../bennyfi-evm-bridge/zero/build/benybridge'),
            contract_name=bridge_z_account
        )
    tevmc.cleos.create_evm_account(bridge_z_account, random_string())
    tevmc.cleos.logger.info('Getting bridge_z_eth_addr...') 
    bridge_z_eth_addr = local_w3.to_checksum_address(tevmc.cleos.eth_account_from_name(bridge_z_account))
    assert bridge_z_eth_addr
    # tevmc.cleos.logger.info('Getting zero_eth_addr...') 
    # zero_eth_addr = local_w3.to_checksum_address(tevmc.cleos.eth_account_from_name('eosio.evm'))
    # assert zero_eth_addr
    quantity_native = Asset.from_str('1000.0000 TLOS')
    quantity_evm = Asset.from_str('100.0000 TLOS')
    tevmc.cleos.transfer_token('eosio', bridge_z_account, quantity_native, 'evm test')
    tevmc.cleos.transfer_token(bridge_z_account, 'eosio.evm', quantity_evm, 'Deposit')
    assert local_w3.eth.get_transaction_count(bridge_z_eth_addr) == 1
    
    tevmc.cleos.logger.info('Deploying MockToken...') 
    mock_token_contract = tevmc.cleos.eth_deploy_contract_from_json(
            Path('../bennyfi-evm-bridge/evm/artifacts/contracts/MockToken.sol/MockToken.json'),
            'MockToken',
            constructor_arguments=['MockToken','MTK', 18]
        )

    assert mock_token_contract.functions.decimals().call() == 18

    # user1 = Account.create()
   user1 = local_w3.eth.accounts[0]
    tevmc.cleos.logger.info('Minting Tokens...') 
    tx_hash = mock_token_contract.functions.mint(user1.address, 10000).transact({'from': tevmc.cleos.evm_default_account.address})
    receipt = local_w3.eth.get_transaction_receipt(tx_hash)
    tevmc.cleos.logger.info('Receipt... %s', json.dumps(receipt, indent=2)) 

    tevmc.cleos.logger.info('Deploying TokenRegistry...') 
    token_registry_contract = tevmc.cleos.eth_deploy_contract_from_json(
            Path('../bennyfi-evm-bridge/evm/artifacts/contracts/TokenRegistry.sol/TokenRegistry.json'),
            'TokenRegistry',
        )
    
    tevmc.cleos.logger.info('Deploying YieldSourceRegistry...') 
    yield_source_registry_contract = tevmc.cleos.eth_deploy_contract_from_json(
            Path('../bennyfi-evm-bridge/evm/artifacts/contracts/YieldSourceRegistry.sol/YieldSourceRegistry.json'),
            'YieldSourceRegistry'
        )
    tevmc.cleos.logger.info('Deploying Bridge E...') 
    bridge_e_contract = tevmc.cleos.eth_deploy_contract_from_json(
            Path('../bennyfi-evm-bridge/evm/artifacts/contracts/BennyfiBridge.sol/BennyfiBridge.json'),
            'BennyfiBridge',
            constructor_arguments=[bridge_z_eth_addr, bridge_z_account,token_registry_contract.address, yield_source_registry_contract.address, bridge_z_eth_addr, 0, 10]
        )

    assert mock_token_contract.functions.decimals().call() == 18
    stake_local_account = 'stakelocal'
    tevmc.cleos.create_account_staked('eosio', 'stakelocal')
    tevmc.cleos.logger.info('Calling init action...') 
    tevmc.cleos.push_action(
        bridge_z_account,
        'init',
        [bridge_e_contract.address[2:],token_registry_contract.address[2:], stake_local_account, 'v1.0', bridge_z_account],
        bridge_z_account
    )

    # breakpoint()
    # tevmc.cleos.logger.info('Getting config table...')   
    # result = tevmc.cleos.get_table(benybridge_account, benybridge_account, 'bridgeconfig')
    # tevmc.cleos.logger.info(json.dumps(result, indent=4))
    # assert result['rows'][0]['version'] == 'v1.0'
    
    # # Test gas price
    # gas_price = local_w3.eth.gas_price
    # tevmc.logger.info(gas_price)
    # assert gas_price <= 120000000000

    # # Test chain ID
    # chain_id = tevmc.config['telos-evm-rpc']['chain_id']
    # assert local_w3.eth.chain_id == chain_id

    # # Test block number
    # assert (local_w3.eth.block_number - tevmc.cleos.get_info()['head_block_num']) < 10

    # # Test transaction count
    # tevmc = tevmc
    # account = tevmc.cleos.new_account()
    # tevmc.cleos.create_evm_account(account, random_string())
    # eth_addr = tevmc.cleos.eth_account_from_name(account)
    # assert eth_addr
    # quantity = Asset.from_str('100.0000 TLOS')
    # tevmc.cleos.transfer_token('eosio', account, quantity, 'evm test')
    # tevmc.cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')
    # assert local_w3.eth.get_transaction_count(local_w3.to_checksum_address(eth_addr)) == 1

    # # Test get transaction receipt
    # account = tevmc.cleos.new_account()
    # tevmc.cleos.create_evm_account(account, random_string())
    # native_eth_addr = tevmc.cleos.eth_account_from_name(account)
    # first_addr = Account.create()
    # second_addr = Account.create()
    # tevmc.cleos.transfer_token('eosio', account, Asset.from_str('100.0000 TLOS'), 'evm test')
    # tevmc.cleos.transfer_token(account, 'eosio.evm', Asset.from_str('100.0000 TLOS'), 'Deposit')
    # tevmc.cleos.eth_transfer(native_eth_addr, first_addr.address, Asset.from_str('90.0000 TLOS'), account=account)

    # quantity = local_w3.eth.get_balance(first_addr.address) - to_wei(2, 'ether')
    # tx_params = {
    #     'from': first_addr.address,
    #     'to': second_addr.address,
    #     'gas': DEFAULT_GAS,
    #     'gasPrice': DEFAULT_GAS_PRICE,
    #     'value': quantity,
    #     'data': b'',
    #     'nonce': 0,
    #     'chainId': tevmc.cleos.chain_id
    # }

    # # test gas estimation
    # gas_est = local_w3.eth.estimate_gas(tx_params)
    # assert gas_est == 26250

    # # test actuall tx send & fetch receipt
    # signed_tx = Account.sign_transaction(tx_params, first_addr.key)
    # tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    # receipt = local_w3.eth.wait_for_transaction_receipt(tx_hash)
    # assert receipt

    # # verify block hash in receipt is valid (metamask does this after getting a receipt)
    # block = local_w3.eth.get_block(receipt['blockHash'])
    # assert block['hash'] == receipt['blockHash']

    # def deploy_new_erc20(name: str, symbol: str, supply: int):
    #     return tevmc.cleos.eth_deploy_contract_from_files(
    #         'tests/evm-contracts/ERC20/TestERC20.abi',
    #         'tests/evm-contracts/ERC20/TestERC20.bin',
    #         name,
    #         constructor_arguments=[name, symbol, supply]
    #     )

    # # test erc20 contract deploy
    # supply = to_wei(69, 'ether')
    # name = 'TestToken'
    # symbol = 'TT'
    # erc20_contract = deploy_new_erc20(name, symbol, supply)

    # assert erc20_contract.functions.name().call() == name
    # assert erc20_contract.functions.symbol().call() == symbol
    # assert erc20_contract.functions.totalSupply().call() == supply

#    # deploy multicall
#    multicall_contract = tevmc.cleos.eth_deploy_contract_from_files(
#        'tests/evm-contracts/multicall/Multicall3.abi',
#        'tests/evm-contracts/multicall/Multicall3.bin',
#        'Multicall3'
#    )
#
#    tokens = []
#    for i in range(3):
#        name = f'MCTest{i}'
#        symbol = f'MCT{i}'
#        supply = to_wei((i + 1) * 10, 'ether')
#        tokens.append(deploy_new_erc20(name, symbol, supply))
#
#    breakpoint()
#
#    # create multi transfer call
#    w3_multicall = W3Multicall(local_w3)
#
#    _from = tevmc.cleos.evm_default_account
#    _to = Account.create()
#
#    for i, token in enumerate(tokens):
#        w3_multicall.add(W3Multicall.Call(token.address, 'symbol()(string)'))
#        w3_multicall.add(W3Multicall.Call(token.address, 'decimals()(uint256)'))
#
#        # w3_multicall.add(W3Multicall.Call(token.address, 'transferFrom(address,address,uint256)(uint256)', [
#        #     _from.address,
#        #     _to.address,
#        #     to_wei(i + 1, 'ether')]))
#
#        # w3_multicall.add(W3Multicall.Call(token.address, 'balanceOf(address)(uint256)', [_from.address]))
#        # w3_multicall.add(W3Multicall.Call(token.address, 'balanceOf(address)(uint256)', [_to.address]))
#
#    result = w3_multicall.call()
#
#    breakpoint()
