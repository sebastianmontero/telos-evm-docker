from util.token import Token
from leap.protocol import Asset

class TokenTestUtil:
    
    @staticmethod
    def assert_stats(token: Token, expected_supply: Asset, issuer: str):
        stats = token.z_stats()
        if expected_supply.amount == 0:
            assert stats is None, f"stats is not None for {token.name}"
        else:
            assert stats["supply"] == str(expected_supply), (
                f"supply does not match {stats['supply']} != {expected_supply}"
            )
            assert stats["max_supply"] == str(token.to_asset(4611686018427387903)), (
                f"max_supply does not match {stats['max_supply']} != {token.to_asset(4611686018427387903)}"
            )
            assert stats["issuer"] == issuer, (
                f"issuer does not match {stats['issuer']} != {issuer} for {token.name}"
            )