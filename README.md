

Для старта контейнера
```local keyclock start 
sudo docker run -p 127.0.0.1:8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:26.7.1 start-dev```

Тут также есть нюансы,во первых надо создать  в keycloack  приложение, второе передать его имя в .env  вместе с этим надо рередать также и client_id  и вот тогда это будет работать