from keycloak import KeycloakOpenID,KeycloakAdmin
import os
from dotenv import load_dotenv
import logging
from faker import Faker
from app.infrastructure.csv_adapter import CsvAdapter



load_dotenv(override=True)
logging.basicConfig(level='INFO')

fake = Faker("ru_RU")


class KeycloakAdminAdapter:

    
    def __init__(self,realm: str):
        """
        Инициализация адаптера 
        """
        self.realm = realm
        self.oidc  = KeycloakOpenID(
                    server_url="http://localhost:8080/",
                    realm_name="master", # тут важно логинимся в мастер реалме
                    client_id="my_app",          
                    client_secret_key=os.getenv("CLIENT_SECRET"),
                )

        
        self._token = self._get_token()
        self.admin = self.connection()  

    def _get_token(self):
        """Получение токена"""
        self._token = self.oidc.token(
                            username="admin",
                            password="admin",
                            grant_type="password",
                            #scope="openid profile email",
                            )
        return self._token

    
    def _refresh_token(self):
        """Нужно для вызова если токен протух"""
        self._get_token()
        self.admin = KeycloakAdmin(
                    server_url="http://localhost:8080/",
                    token = self._token,
                    realm_name=self.realm,
                    #user_realm_name="only_if_other_realm_than_master",
                    pool_maxsize=20)



    def check_token(self):
        """Проверяем жив ли токен"""
        try:
            self.admin.get_server_info()
        except Exception as e:
            """Проверка связана ли ошибка с авторизацией"""
            if "401" in str(e) or "Unauthorized" in str(e):
                self._refresh_token()
            else:
                logging.error(f"Ошибка связанная с проверкой токена. Текст ошибки {e}")

        
        

    def connection(self):
        admin = KeycloakAdmin(
            server_url="http://localhost:8080/",
            token = self._token,
            realm_name=self.realm,
            #user_realm_name="only_if_other_realm_than_master",
            pool_maxsize=20)
        return admin

    def get_token(self):
        """ Это пока что штука для тестов будет немного изменена когда мы будем получать токен при авторизации юзера"""
        

        token_response = self.oidc.token(
            username="admin",
            password="admin",
            grant_type="password",
            scope="openid profile email",
        )

        return token_response
        
       
    def create_user(self, email: str,
                    username: str,
                    enabled: bool,
                    firstname: str,
                    lastname: str) -> str:
        """The user creation"""
        self.check_token()
        try:
            new_user = self.admin.create_user({"email": email,
                                        "username": username,
                                        "enabled": enabled,
                                        "firstName": firstname,
                                        "lastName": lastname})
            logging.info(f'Пользователь с почтой {email} создан')
            return new_user
        except Exception as e:
            logging.error(f'Ошибка создания. Текст ошибки: {e}')
            return None


    def get_users(self)-> list:
        """ Get users lists"""
        self.check_token()
        try:
            users = self.admin.get_users({})
            return users
        except Exception as e:
            logging.error(f"Не удалось получить список пользователей. Ошибка {e}")
            return None

    def create_from_list(self, list_of_dicts: list ):
        for dict in list_of_dicts:
            self.create_user(email=dict.get('email'),
                             username=dict.get("email"),
                             enabled=dict.get("enabled"),
                             lastname=dict.get("lastname"),
                             firstname=dict.get("firstname")
            )

        
        


# здесь пока играемся
# admin = KeycloakAdminAdapter("test")

# csv_adapter = CsvAdapter()
# users = csv_adapter.get_list_dicts("file.csv")
# admin.create_from_list(users)


# print(admin.get_token())



# print(admin.create_user(email=fake.email(),
#                         username=fake.user_name(),
#                         enabled=fake.boolean(),
#                         firstname=fake.first_name(),
#                         lastname=fake.last_name()))


# users = admin.get_users()
# for user in users:
#     print("User")
#     print("__________")
#     print(user)
#     print("___________")