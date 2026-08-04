from keycloak import KeycloakAdmin
import os
from dotenv import load_dotenv
import logging




load_dotenv(override=True)
logging.basicConfig(level='INFO')


keycloak_admin = KeycloakAdmin(
                        server_url=os.getenv('KEYCLOAK_URL'),
                        username=os.getenv('KEYCLOAK_ADMIN_PASSWORD'),
                        password=os.getenv('PASSWORD'),
                        realm_name="master",
                        client_id="admin-cli",
                        grant_type="password",
                        pool_maxsize=25,
                        verify=True)


class KeycloakAdapter:

    def create_user():
        pass

    def update_user():
        pass

    def get_user_by_username():
        pass

    def get_all_users():
        pass

    def delete_user():
        pass