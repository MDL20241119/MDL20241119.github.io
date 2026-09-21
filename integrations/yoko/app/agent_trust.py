"""Pinned A2A Card signatures. Trust never supplies user/booking authorization."""
import json
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from google.protobuf.json_format import MessageToDict, ParseDict
from jwt.exceptions import InvalidKeyError
from jwt.utils import base64url_decode
from a2a.types import a2a_pb2 as p
from a2a.utils.signing import create_agent_card_signer, create_signature_verifier
from a2a.utils.proto_utils import validate_proto_required_fields

from .external_auth import epoch, https_url, text_value


def signer(key_file, key_id):
    if not text_value(key_id, 100): raise ValueError('A key ID is required')
    key = serialization.load_pem_private_key(Path(key_file).read_bytes(), password=None)
    if not isinstance(key, RSAPrivateKey) or key.key_size < 2048: raise ValueError('RSA private key of at least 2048 bits required')
    return create_agent_card_signer(key, {'alg': 'RS256', 'kid': key_id, 'typ': 'JOSE'})


def verify_card(raw, trust, now):
    """Verify downloaded bytes against an operator supplied, expiring trust pin.

No jku URL is dereferenced. A valid signature alone cannot add a client to the
resource server allowlist or enroll a passenger, and cannot execute a booking.
"""
    if len(raw) > 32768: raise ValueError('Card too large')
    if not epoch(trust['expires_at']) or trust['expires_at'] <= now: raise ValueError('Agent trust has expired')
    endpoint, discovery = https_url(trust['endpoint']), https_url(trust['authorization_metadata'])
    if not text_value(trust['key_id'], 100): raise ValueError('Invalid pinned key ID')
    key = serialization.load_pem_public_key(Path(trust['public_key_file']).read_bytes())
    if not isinstance(key, RSAPublicKey) or key.key_size < 2048: raise ValueError('RSA public key of at least 2048 bits required')
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj: raise ValueError('Duplicate Card key')
            obj[k] = v
        return obj
    try:
        value = json.loads(raw, object_pairs_hook=unique)
        card = ParseDict(value, p.AgentCard()); validate_proto_required_fields(card)
        if not 1 <= len(card.signatures) <= 8: raise ValueError('Signed Card required')
        for signature in card.signatures:
            header = json.loads(base64url_decode(signature.protected.encode()), object_pairs_hook=unique)
            if set(header)-{'alg','kid','typ'} or header.get('alg') != 'RS256' or header.get('typ') != 'JOSE' or header.get('kid') != trust['key_id']:
                raise ValueError('Untrusted signature header')
        def key_provider(kid, jku):
            if kid != trust['key_id'] or jku is not None: raise InvalidKeyError('Only the pinned key is allowed')
            return key
        create_signature_verifier(key_provider, ['RS256'])(card)
        interfaces = MessageToDict(card)['supportedInterfaces']
        if interfaces != [{'url': endpoint, 'protocolBinding': 'JSONRPC', 'protocolVersion': '1.0'}]:
            raise ValueError('Card endpoint/protocol does not match the trust pin')
        schemes = MessageToDict(card).get('securitySchemes', {})
        if schemes.get('oauth', {}).get('openIdConnectSecurityScheme', {}).get('openIdConnectUrl') != discovery:
            raise ValueError('Card authentication provider does not match the trust pin')
        return card
    except Exception as error:
        # Do not expose signature/key/parser details to an external client.
        raise ValueError('Card signature or pinned identity could not be verified') from error
