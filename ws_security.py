import base64
import hashlib
import os
from datetime import datetime, timedelta


def gerar_ws_security(usuario, senha):
    dt_now = datetime.utcnow()
    created = dt_now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    expires = (dt_now + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    raw_nonce = os.urandom(12)
    nonce_b64 = base64.b64encode(raw_nonce).decode()
    digest = hashlib.sha1(raw_nonce + created.encode("utf-8") + senha.encode("utf-8")).digest()
    password_digest = base64.b64encode(digest).decode()

    return f"""
<wsse:Security soapenv:mustUnderstand="1"
  xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
  xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <wsu:Timestamp wsu:Id="TS-{os.urandom(8).hex().upper()}">
        <wsu:Created>{created}</wsu:Created>
        <wsu:Expires>{expires}</wsu:Expires>
    </wsu:Timestamp>
    <wsse:UsernameToken wsu:Id="UsernameToken-{os.urandom(8).hex().upper()}">
        <wsse:Username>{usuario}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{password_digest}</wsse:Password>
        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</wsse:Nonce>
        <wsu:Created>{created}</wsu:Created>
    </wsse:UsernameToken>
</wsse:Security>"""
