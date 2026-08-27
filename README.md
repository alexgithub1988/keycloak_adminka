

Для старта контейнера
```local keyclock start 
sudo docker run -p 127.0.0.1:8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:26.7.1 start-dev```

Версия 24.0.2
`sudo docker run --rm -p 127.0.0.1:8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:24.0.2 start-dev`

Тут также есть нюансы,во первых надо создать  в keycloack  приложение, второе передать его имя в .env  вместе с этим надо передать также и client_id  и вот тогда это будет работать и включить аутификацию тогда появятся креды в клиенте