# Дипломный проект — сайт Foodgram, «Продуктовый помощник».
![Workflow Status](https://github.com/YuraKvaskov/foodgram-project-react/actions/workflows/foodgram.yml/badge.svg)

На этом сервисе пользователи смогут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а перед походом в магазин скачивать сводный список продуктов, необходимых для приготовления одного или нескольких выбранных блюд.

## Как развернуть проект на сервере:

Установите соединение с сервером:

```
ssh username@server_address
```
Проверьте статус nginx:

```
sudo service nginx status
```
Если nginx запущен, остановите его:

```
sudo systemctl stop nginx
```
Установите Docker и Docker-compose:

```
sudo apt install docker.io
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```
Проверьте корректность установки Docker-compose:

```
sudo  docker-compose --version
```
Перенесите из папки infra где находятся заготовка инфраструктуры проекта: конфигурационный файл nginx и docker-compose.yml.
```
scp docker-compose.yml nginx.conf foodgram@158.160.34.226:/home/foodgram/
```
После деплоя:
Соберите статические файлы (статику):

```
sudo docker-compose exec web python manage.py collectstatic --no-input
```
Примените миграции:

```
(опционально) sudo docker-compose exec web python manage.py makemigrations
sudo docker-compose exec web python manage.py migrate --noinput
```
Создайте суперпользователя:

```
sudo docker-compose exec web python manage.py createsuperuser

Проект запустится на адресе http://localhost, увидеть спецификацию API вы сможете по адресу http://localhost/api/docs/
