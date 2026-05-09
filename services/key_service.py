import secrets


def generate_site_id():
    return 'SITE_' + secrets.token_hex(8)



def generate_public_key():
    return 'pk_' + secrets.token_hex(24)



def generate_secret_key():
    return 'sk_' + secrets.token_hex(32)