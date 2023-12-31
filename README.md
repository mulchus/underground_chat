# Скрипт для чтения подпольного чата
## underground_chat

## Установка

[Установите Python](https://www.python.org/), если этого ещё не сделали.

Проверьте, что `python` установлен и корректно настроен.  
Запустите его в командной строке:
```sh
python --version
```

Скачайте код командой  
```shell
git clone https://github.com/mulchus/underground_chat.git
```

В каталоге проекта создайте виртуальное окружение:  
```sh
python -m venv venv
```

Активируйте его. На разных операционных системах это делается разными командами:  
- Windows: `.\venv\Scripts\activate`
- MacOS/Linux: `source venv/bin/activate`

Установите зависимости командой   
```shell
pip install -r requirements.txt
```


## Настройки

Настроки могут браться как из отдельного файла, так и из аргументов командной строки при запуске скрипта (вторые имеют больший приоритет).    
Чтобы их определить, создайте файл `.env` в корне проекта и запишите туда данные в таком формате `ПЕРЕМЕННАЯ=значение`:  

- `HOST` - хост подключаемого сервера, по умолчанию `minechat.dvmn.org`  
- `CLIENT_PORT` - порт на хосте подключаемого сервера для чтения переписки, по умолчанию `5000`  
- `SENDER_PORT` - порт на хосте подключаемого сервера для регистрации пользователя и отправки сообщений, по умолчанию `5050`  
- `HISTORY` - относительный путь к файлу сообщений чата, включая имя файла, по умолчанию `chat.txt`  
- `TOKEN` - account_hash, выдаваемый при регистрации нового пользователя в чате  
- `NICKNAME` - составное имя при регистрации нового пользователя в чате (компонуется сервером)  

или аналогичные переменные в командной строке (высокий приоритет):  
- --host [HOST]
- --client_port [PORT]
- --sender_port [PORT]
- --history [HISTORY]
- --token [TOKEN]
- --nickname [NICKNAME]


## Запуск
Запустите скрипт командой  
```shell
python main.py [настройки командной строки]
```
например:
```shell
python3 main.py --host minechat.dvmn.org --client_port 5000 --history chat/1.txt
```


## Регистрация нового юзера в чате
Есои не был задан `token`, то при запуске скрипта вначале появится окно регистрации нового юзера.  
Необходимо ввести имя.   
Скрипт запишет полное имя и токен вновь созданного юзера в файл .env.   
Окно регистрации  
![reg](https://github.com/mulchus/underground_chat/assets/111083714/42421773-2fcf-4a95-a60b-13c525438e43)


## Пример работы скрипта
![chat](https://github.com/mulchus/underground_chat/assets/111083714/f21922e3-ab98-42d1-8062-78b5bbc25f92)

После повторного запуска скрипта сначала в окно чата подгрузятся старые сообщения, что может занять некоторое время.  


# Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).
