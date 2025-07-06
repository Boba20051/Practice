import socket
import threading
import time
import json
from datetime import datetime


class ChatServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        self.clients = {}
        self.lock = threading.Lock()
        self.running = True
        self.log("Сервер запущен")
        self.message_history = []  # Для хранения истории сообщений
        self.history_file = "chat_history.json"  # Файл для сохранения
        self.load_history()  # Загрузка истории при старте

    def save_history(self):
        """Сохраняет историю в JSON файл"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.message_history, f, ensure_ascii=False, indent=2)

    def load_history(self):
        """Загружает историю из файла"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.message_history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.message_history = []

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def broadcast(self, data, sender=None):
        """Модифицированный метод рассылки с сохранением"""
        if data["type"] == "message":
            self.message_history.append({
                "time": data["time"],
                "from": data["from"],
                "text": data["text"]
            })
            self.save_history()  # Сохраняем после каждого сообщения

        with self.lock:
            for client, (nickname, addr) in list(self.clients.items()):
                try:
                    if client != sender:
                        client.send(json.dumps(data).encode('utf-8'))
                except Exception as e:
                    self.log(f"Ошибка отправки {addr}: {e}")
                    self.remove_client(client)

    def update_userlist(self):
        userlist = {
            "type": "userlist",
            "users": [nickname for _, (nickname, _) in self.clients.items()]
        }
        self.broadcast(userlist)

    def handle_client(self, client, addr):
        try:
            nickname = client.recv(1024).decode('utf-8')
            if not nickname:
                raise Exception("Пустой никнейм")



            # Отправляем историю сообщений по одному
            for msg in self.message_history[-100:]:  # Последние 100 сообщений
                try:
                    # Формируем каждое сообщение истории как обычное сообщение
                    history_msg = {
                        "type": "message",
                        "from": msg["from"],
                        "text": msg["text"],
                        "time": msg["time"],
                        "is_history": True  # Добавляем флаг, что это из истории
                    }
                    client.send(json.dumps(history_msg).encode('utf-8'))
                    time.sleep(0.05)  # Небольшая задержка между сообщениями
                except Exception as e:
                    self.log(f"Ошибка отправки истории {addr}: {e}")
                    break

            with self.lock:
                self.clients[client] = (nickname, addr)
            self.log(f"{nickname} подключился ({addr[0]}:{addr[1]})")

            # Отправляем системное сообщение о подключении
            system_msg = {
                "type": "system",
                "text": f"{nickname} присоединился к чату"
            }
            self.broadcast(system_msg)
            self.update_userlist()
            while True:
                message = client.recv(1024).decode('utf-8')
                if not message:
                    break
                if message.startswith("PING"):
                    client.send("PONG".encode('utf-8'))
                else:
                    # Формируем сообщение с временной меткой
                    msg_data = {
                        "type": "message",
                        "from": nickname,
                        "text": message,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "is_history": False  # Новое сообщение, не из истории
                    }
                    self.broadcast(msg_data, client)
        except Exception as e:
            self.log(f"Ошибка клиента {addr}: {e}")
        finally:
            self.remove_client(client)

    def remove_client(self, client):
        with self.lock:
            if client in self.clients:
                nickname, addr = self.clients[client]
                del self.clients[client]
                client.close()
                self.log(f"{nickname} отключился")
                system_msg = {
                    "type": "system",
                    "text": f"{nickname} покинул чат"
                }
                self.broadcast(system_msg)
                self.update_userlist()

    def start(self):
        try:
            while self.running:
                client, addr = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(client, addr))
                thread.daemon = True
                thread.start()
        except Exception as e:
            if self.running:
                self.log(f"Ошибка сервера: {e}")
        finally:
            self.server.close()

    def stop(self):
        self.running = False
        dummy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dummy.connect((self.host, self.port))
        dummy.close()
        self.log("Сервер остановлен")


if __name__ == "__main__":
    server = ChatServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()