import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import time


class ChatClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Чат")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.nickname = ""
        self.client_socket = None
        self.connected = False

        self.setup_ui()
        self.connect_to_server()

    def setup_ui(self):
        # Сетка интерфейса
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Список пользователей
        self.user_frame = tk.Frame(self.root)
        self.user_frame.grid(row=0, column=1, sticky="ns", padx=5, pady=5)

        tk.Label(self.user_frame, text="Онлайн:").pack()
        self.user_listbox = tk.Listbox(self.user_frame, width=15)
        self.user_listbox.pack(fill="both", expand=True)

        # Чат
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.chat_text = tk.Text(self.chat_frame, state="disabled")
        self.chat_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.chat_text.tag_config("system", foreground="gray")
        self.chat_text.tag_config("my_message", foreground="blue")
        self.chat_text.tag_config("other_message", foreground="black")

        self.input_frame = tk.Frame(self.chat_frame)
        self.input_frame.pack(fill="x", padx=5, pady=5)

        self.message_entry = tk.Entry(self.input_frame)
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(self.input_frame, text="Отправить", command=self.send_message)
        self.send_button.pack(side="right")

    def connect_to_server(self):
        server_ip = simpledialog.askstring("Подключение", "IP сервера:", initialvalue="127.0.0.1")
        if not server_ip:
            self.root.destroy()
            return

        server_port = simpledialog.askinteger("Подключение", "Порт сервера:", initialvalue=5555)
        if not server_port:
            self.root.destroy()
            return

        self.nickname = simpledialog.askstring("Никнейм", "Введите ваш никнейм:")
        if not self.nickname:
            self.root.destroy()
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, server_port))
            self.client_socket.send(self.nickname.encode('utf-8'))
            self.connected = True
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться: {e}")
            self.root.destroy()

    def receive_messages(self):
        while self.connected:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    break

                data = json.loads(message)

                if data["type"] == "system":
                    self.display_system_message(data["text"])
                elif data["type"] == "message":
                    self.display_message(
                        data["from"],
                        data["text"],
                        data["time"],
                        is_me=(data["from"] == self.nickname),
                        is_history=data.get("is_history", False)
                    )
                elif data["type"] == "userlist":
                    self.update_user_list(data["users"])

            except json.JSONDecodeError:
                pass
            except Exception as e:
                self.display_system_message(f"Ошибка соединения: {e}")
                self.connected = False
                break

    def update_user_list(self, users):
        self.user_listbox.delete(0, "end")
        for user in users:
            if user:
                self.user_listbox.insert("end", user)

    def display_system_message(self, text):
        self.chat_text.config(state="normal")
        self.chat_text.insert("end", f"⚡ {text}\n", "system")
        self.chat_text.config(state="disabled")
        self.chat_text.see("end")

    def display_message(self, sender, text, timestamp, is_me=True, is_history=False):
        self.chat_text.config(state="normal")
        if is_me:
            prefix = "Я"
            tag = "my_message"
        else:
            prefix = sender
            tag = "other_message"

        # Если сообщение из истории, делаем его немного бледнее
        if is_history:
            self.chat_text.tag_config("history_message", foreground="#888888")
            tag = "history_message"

        self.chat_text.insert(
            "end",
            f"[{timestamp}] {prefix}: {text}\n",
            tag
        )
        self.chat_text.config(state="disabled")
        self.chat_text.see("end")

    def send_message(self, event=None):
        message = self.message_entry.get()
        if message and self.connected:
            try:
                # Локальное отображение своего сообщения
                self.display_message(
                    self.nickname,
                    message,
                    time.strftime("%H:%M:%S"),
                    is_me=True
                )

                # Отправка на сервер
                self.client_socket.send(message.encode('utf-8'))
                self.message_entry.delete(0, "end")
            except Exception as e:
                self.display_system_message(f"Ошибка отправки: {e}")
                self.connected = False

    def on_close(self):
        if self.connected:
            try:
                self.client_socket.close()
            except:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    client = ChatClient()
    client.run()