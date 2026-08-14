from keycloak import KeycloakOpenID,KeycloakAdmin
import os
from dotenv import load_dotenv
import logging
from faker import Faker



load_dotenv(override=True)
logging.basicConfig(level='INFO')

fake = Faker("ru_RU")


class KeycloakAdminAdapter:

    def __init__(self,username,password,realm):
        """We are getting parameters for login and next manipulation"""
        self._username = username
        self._password = password
        self.realm = realm


        self.admin = KeycloakAdmin(
            server_url="http://localhost:8080/",
            username=self._username,
            password=self._password,
            realm_name=self.realm,
            #user_realm_name="only_if_other_realm_than_master",
            pool_maxsize=20)
        
       
    def create_user(self, email: str,
                    username: str,
                    enabled: bool,
                    firstname: str,
                    lastname: str) -> str:
        """The user creation"""
        try:
            new_user = self.admin.create_user({"email": email,
                                        "username": username,
                                        "enabled": enabled,
                                        "firstName": firstname,
                                        "lastName": lastname})
            return new_user
        except Exception as e:
            logging.error(f'Ошибка создания. Текст ошибки: {e}')
            return None


    def get_users(self)-> list:
        """ Get users lists"""
        try:
            users = self.admin.get_users({})
            return users
        except Exception as e:
            logging.error(f"Не удалось получить список пользователей. Ошибка {e}")
            return None

        
        



admin = KeycloakAdminAdapter('admin','admin','master')


# print(admin.create_user(email=fake.email(),
#                         username=fake.user_name(),
#                         enabled=fake.boolean(),
#                         firstname=fake.first_name(),
#                         lastname=fake.last_name()))
        
print(admin.get_users())
