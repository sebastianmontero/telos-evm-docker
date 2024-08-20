from eth_abi import encode
from web3 import Web3

class FunctionEncoder:
    
    @staticmethod
    def encode_short_string(input_str: str) -> bytes:
        # Check if the string is too long
        if len(input_str.encode('utf-8')) >= 32:
            raise ValueError("string must be less than 32 bytes")
        
        # Create a bytearray of 32 bytes, initialized with zeros
        result = bytearray(32)
        
        # Copy the string bytes into the result
        encoded_input = input_str.encode('utf-8')
        result[:len(encoded_input)] = encoded_input
        
        # Encode the length in the last byte
        encoded_length = len(encoded_input) * 2 + 1
        result[31] = encoded_length
        
        return bytes(result)
    
    
    def __init__(self, function_name, parameter_types):
        self.function_name = function_name
        self.parameter_types = parameter_types
        self.function_signature = f"{function_name}({','.join(parameter_types)})"
        self.function_selector = self._get_function_selector()

    def _get_function_selector(self):
        return Web3.keccak(text=self.function_signature)[:4]

    def get_function_selector(self):
        return self.function_selector

    def encode_arguments(self, *args):
        if len(args) != len(self.parameter_types):
            raise ValueError("Number of arguments does not match number of parameter types")
        processed_args = []
        for arg, parameter_type in zip(args, self.parameter_types):
            if parameter_type == 'bytes32' and isinstance(arg, str):
                processed_args.append(self.encode_short_string(arg))
            else:
                processed_args.append(arg)
        return encode(self.parameter_types, processed_args)

    def encode_function_call(self, *args):
        encoded_args = self.encode_arguments(*args)
        return (self.function_selector + encoded_args)
