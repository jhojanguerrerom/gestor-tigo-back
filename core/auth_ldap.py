import logging
from ldap3 import Server, Connection, SIMPLE, ALL

LDAP_SERVER = "ldap://10.100.65.10:389"
LDAP_DOMAIN = "epmtelco.com.co"
LDAP_TREE = "dc=epmtelco,dc=com,dc=co"

logger = logging.getLogger("auth_ldap")

def authenticate_user(username: str, password: str):
    user_dn = f"{username}@{LDAP_DOMAIN}"

    try:
        # No pedimos demasiada info del server (evita timeout si TLS no está activo)
        server = Server(LDAP_SERVER, get_info=None)

        # Conexión simple (sin STARTTLS, sin auto_bind)
        conn = Connection(
            server,
            user=user_dn,
            password=password,
            authentication=SIMPLE,
            raise_exceptions=True,
        )

        # Intentamos el bind manualmente
        if not conn.bind():
            logger.error(f"Error al iniciar sesión: {conn.last_error}")
            return None

        # Si quieres verificar que el usuario existe:
        conn.search(
            search_base=LDAP_TREE,
            search_filter=f"(sAMAccountName={username})",
            attributes=["displayName", "mail"],
        )

        user_info = conn.entries[0] if conn.entries else None

        conn.unbind()

        return {
            "username": username,
            "display_name": getattr(user_info, "displayName", username),
            "email": getattr(user_info, "mail", None),
        }

    except Exception as e:
        logger.error(f"LDAP Auth failed: {e}")
        return None