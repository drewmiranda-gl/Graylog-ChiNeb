import json
import configparser
import ssl
from ldap3 import Server, Connection, ALL, SIMPLE, Tls
from datetime import datetime

def query_active_directory():
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')

        AD_SERVER = config.get('ad_credentials', 'server')
        AD_USER = config.get('ad_credentials', 'user')
        AD_PASSWORD = config.get('ad_credentials', 'password')
        SEARCH_BASE = config.get('ad_credentials', 'search_base')
        CA_CERT_FILE = config.get('ad_credentials', 'ca_cert_file')
    except Exception as e:
        print(f"Error reading config.ini file: {e}")
        return None

    domain_parts = [part.split('=')[1] for part in SEARCH_BASE.split(',') if 'DC=' in part]
    domain_name = '.'.join(domain_parts)
    BIND_USER = f"{AD_USER}@{domain_name}"
    
    # Uncomment for Secure LDAP connection. Make sure to get Certificate for your AD and either rename it to ca_cert.cer or change the file name in the config.ini
    # tls_config = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=CA_CERT_FILE)
    # server = Server(AD_SERVER, get_info=ALL, use_ssl=True, tls=tls_config)
    
    # Uncomment if you want to use a not secure connection to your LDAP. If using a this method, create a blank file called ca_cert.cer
    # server = Server(AD_SERVER, get_info=ALL, use_ssl=False)
    
    try:
        # Note: SIMPLE authentication over non-SSL sends credentials in plaintext.
        conn = Connection(server, user=BIND_USER, password=AD_PASSWORD, authentication=SIMPLE, auto_bind=True)
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

    attributes_to_get = [
        'cn', 'givenName', 'sn', 'sAMAccountName', 'description',
        'employeeID', 'mail', 'whenCreated', 'pwdLastSet', 'whenChanged',
        'accountExpires', 'lastLogon', 'lastLogoff', 'lockoutTime', 'memberOf',
        'userAccountControl'
    ]

    all_users = []
    
    entry_generator = conn.extend.standard.paged_search(
        search_base=SEARCH_BASE,
        search_filter='(objectCategory=person)',
        search_scope='SUBTREE',
        attributes=attributes_to_get,
        paged_size=500,
        generator=True
    )

    for entry in entry_generator:
        if entry['type'] != 'searchResEntry':
            continue

        user_data = {}
        raw_attrs = entry['attributes']

        # --- CORRECTED ATTRIBUTE PROCESSING LOOP ---
        for attr in attributes_to_get:
            value = raw_attrs.get(attr)

            # This check now handles both missing attributes (None) and empty lists ([])
            if not value:
                user_data[attr] = None
                continue

            # Handle multi-valued attributes (like memberOf)
            if isinstance(value, list) and len(value) > 1:
                user_data[attr] = [str(item) for item in value]
            else:
                # Handle single values, which could be in a list or be a direct object
                item = value[0] if isinstance(value, list) else value
                
                # Properly format datetime objects for JSON
                if isinstance(item, datetime):
                    user_data[attr] = item.isoformat()
                else:
                    user_data[attr] = str(item)

        uac_value = raw_attrs.get('userAccountControl', 0)
        if isinstance(uac_value, list):
            uac_value = uac_value[0] if uac_value else 0

        is_disabled = bool(int(uac_value) & 2)
        user_data['disabled_account'] = is_disabled
        
        if 'userAccountControl' in user_data:
            del user_data['userAccountControl']

        all_users.append(user_data)

    conn.unbind()
    return all_users

if __name__ == "__main__":
    users = query_active_directory()
    if users:
        output_filename = 'ad_users.json'
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        print(f"✅ Successfully exported {len(users)} user accounts to '{output_filename}'")
    else:
        print("❌ No users were exported. Please check the logs for errors.")