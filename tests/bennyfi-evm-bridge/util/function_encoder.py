from eth_abi import encode
from web3 import Web3

class FunctionEncoder:
    def __init__(self, function_name, parameter_types):
        self.function_name = function_name
        self.parameter_types = parameter_types
        self.function_signature = f"{function_name}({','.join(parameter_types)})"
        self.function_selector = self._get_function_selector()

    def _get_function_selector(self):
        return Web3.keccak(text=self.function_signature)[:4]

    def get_function_selector(self):
        return self.function_selector.hex()

    def encode_arguments(self, *args):
        if len(args) != len(self.parameter_types):
            raise ValueError("Number of arguments does not match number of parameter types")
        return encode(self.parameter_types, args)

    def encode_function_call(self, *args):
        encoded_args = self.encode_arguments(*args)
        return (self.function_selector + encoded_args).hex()