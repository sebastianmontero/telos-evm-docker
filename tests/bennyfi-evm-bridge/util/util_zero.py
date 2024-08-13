from leap.cleos import CLEOS
from leap.tokens import DEFAULT_SYS_TOKEN_CODE

class UtilZero:
  def __init__(self, cleos: CLEOS):
    self.cleos = cleos

  def create_delegated_account(
        self,
        owner: str,
        name: str,
        delegated_to: str,
        delegated_permission: str = 'active',
        net: str = f'10.0000 {DEFAULT_SYS_TOKEN_CODE}',
        cpu: str = f'10.0000 {DEFAULT_SYS_TOKEN_CODE}',
        ram: int = 10_000_000,
    ) -> tuple[int, dict]:
        '''Creates a new staked blockchain account.

        :param owner: The account that will own the new account.
        :type owner: str
        :param name: The new account name.
        :type name: str
        :param delegated_to: The account to delegate to.
        :type key: str
        :param delegated_permission: The permission to delegate to. Defaults to 'active'.
        :type key: str
        :param net: Amount of NET to stake. Defaults to \"10.0000 TLOS\".
        :type net: str 
        :param cpu: Amount of CPU to stake. Defaults to \"10.0000 TLOS\".
        :type cpu: str 
        :param ram: Amount of RAM to buy in bytes. Defaults to 10,000,000.
        :type ram: int
        

        :return: Exit code and response dictionary.
        :rtype: tuple[int, dict]
        '''

        actions = [{
            'account': 'eosio',
            'name': 'newaccount',
            'data': [
                owner, name,
                {'threshold': 1, 'keys': [], 'accounts': [{"permission":{"actor":delegated_to,"permission":delegated_permission},"weight":1}], 'waits': []},
                {'threshold': 1, 'keys': [], 'accounts': [{"permission":{"actor":delegated_to,"permission":delegated_permission},"weight":1}], 'waits': []}
            ],
            'authorization': [{
                'actor': owner,
                'permission': 'active'
            }]
        }, {
            'account': 'eosio',
            'name': 'buyrambytes',
            'data': [
                owner, name, ram
            ],
            'authorization': [{
                'actor': owner,
                'permission': 'active'
            }]
        }, {
            'account': 'eosio',
            'name': 'delegatebw',
            'data': [
                owner, name,
                net, cpu, True
            ],
            'authorization': [{
                'actor': owner,
                'permission': 'active'
            }]
        }]

        return self.cleos.push_actions(
            actions, self.cleos.private_keys[owner])