#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import sqlite3
import os
import getpass
import subprocess
from datetime import datetime
import sys
import socket
import select
import termios
import tty
import time

# Function to clear screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Function to establish an SSH connection
def ssh_connect(ip, user, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print("[INFO] Trying to connect to {} as {}...".format(ip, user))
        client.connect(ip, username=user, password=password, timeout=10)
        print("[INFO] Successfully connected to {}".format(ip))

        channel = client.invoke_shell(term='xterm', width=80, height=24)

        # Save original terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            channel.settimeout(0.0)

            while True:
                r, w, e = select.select([channel, sys.stdin], [], [])
                if channel in r:
                    try:
                        data = channel.recv(1024)
                        if len(data) == 0:
                            break
                        sys.stdout.write(data.decode('utf-8'))
                        sys.stdout.flush()
                    except socket.timeout:
                        pass

                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        break

                    # Handle special keys
                    if ord(x) == 3:  # Ctrl-C
                        channel.send('\x03')
                    elif ord(x) == 4:  # Ctrl-D
                        channel.send('\x04')
                    elif ord(x) == 9:  # Tab
                        channel.send('\t')
                    elif ord(x) == 127:  # Backspace
                        channel.send('\x7f')
                    elif ord(x) == 27:  # Escape sequences (arrow keys)
                        next1 = sys.stdin.read(1)
                        next2 = sys.stdin.read(1)
                        if next1 == '[':
                            if next2 == 'A':  # Up arrow
                                channel.send('\x1b[A')
                            elif next2 == 'B':  # Down arrow
                                channel.send('\x1b[B')
                            elif next2 == 'C':  # Right arrow
                                channel.send('\x1b[C')
                            elif next2 == 'D':  # Left arrow
                                channel.send('\x1b[D')
                    else:
                        channel.send(x)

        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        channel.close()
        client.close()
        print("[INFO] Connection closed.")

    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Check login and password.")
    except paramiko.SSHException as e:
        print("[ERROR] Cannot establish connection: {}".format(e))
    except Exception as e:
        print("[ERROR] An error occurred: {}".format(e))

# Function to check if a connection already exists
def connection_exists(ip, user):
    conn = sqlite3.connect('connections.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM connections WHERE ip = ? AND user = ?', (ip, user))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# Function to save connection data to the database
def save_connection_data(name, ip, user, password):
    if not connection_exists(ip, user):
        conn = sqlite3.connect('connections.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS connections
                         (id INTEGER PRIMARY KEY, name TEXT, ip TEXT, user TEXT, password TEXT, date TEXT)''')
        cursor.execute('''INSERT INTO connections (name, ip, user, password, date) VALUES (?, ?, ?, ?, ?)''',
                       (name, ip, user, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        print("Connection saved successfully.")
    else:
        print("Connection already exists in database.")

# Function to delete a connection
def delete_connection(connection_id):
    conn = sqlite3.connect('connections.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM connections WHERE id = ?', (connection_id,))
    conn.commit()
    conn.close()

# Function to get saved connections from the database
def get_saved_connections():
    conn = sqlite3.connect('connections.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS connections
                     (id INTEGER PRIMARY KEY, name TEXT, ip TEXT, user TEXT, password TEXT, date TEXT)''')
    conn.commit()

    cursor.execute('SELECT id, name, ip, user, password FROM connections')
    saved_connections = cursor.fetchall()
    conn.close()
    return saved_connections

def print_ascii_art():
    print("Copyright (c) 2024 Esikava (Архипов Владимир Евгеньевич)")
    print()

def loading_screen():
    clear_screen()
    license_text = """
MIT License

Copyright (c) 2024 Esikava (Архипов Владимир Евгеньевич)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    print(license_text)
    time.sleep(7)
    clear_screen()

# Main application function
def main():
    add_name_column()

    loading_screen() # Вызов загрузочного экрана

    saved_connections = get_saved_connections()

    while True:
        clear_screen()
        print_ascii_art()
        print("Welcome to SSH Connector!")
        print("-" * 26)

        print("\nMenu:")
        if saved_connections:
            print("\nSaved connections:")
            for i, (id, name, ip, user, _) in enumerate(saved_connections):
                print("{}. {} - IP: {}, User: {}".format(i + 1, name, ip, user))
        print("\n0. Manual input")
        print("d. Delete connections")
        print("q. Quit")

        choice = input("\nEnter your choice: ")

        if choice.lower() == 'q':
            print("\nGoodbye!")
            break

        elif choice.lower() == 'd':
            while True:
                clear_screen()
                print("Delete Connections Menu")
                print("-" * 30)

                connections = get_saved_connections()
                if not connections:
                    print("\nNo saved connections found.")
                    input("\nPress Enter to return to main menu...")
                    break

                print("\nSaved connections:")
                for i, (conn_id, name, ip, user, _) in enumerate(connections):
                    print("{}. {} - IP: {}, User: {}".format(i + 1, name, ip, user))
                print("0. Return to main menu")

                choice = input("\nEnter connection ID to delete or 0 to return: ")

                if choice == '0':
                    break

                if choice.isdigit():
                    delete_id = int(choice)

                    if 1 <= delete_id <= len(connections):
                        connection_id = connections[delete_id -1][0]
                        delete_connection(connection_id)
                        print("\nConnection deleted successfully.")
                        saved_connections = get_saved_connections()
                        input("\nPress Enter to continue...")
                    else:
                        print("\nInvalid connection ID.")
                        input("\nPress Enter to continue...")
                else:
                    print("\nInvalid input.")
                    input("\nPress Enter to continue...")

        elif choice.isdigit():
            choice = int(choice)
            if choice == 0:
                name = input("Enter connection name: ")
                ip = input("Enter IP address: ")
                user = input("Enter username: ")
                password = getpass.getpass("Enter password: ")

                if not connection_exists(ip, user):
                    try:
                        ssh_connect(ip, user, password)
                        save_connection_data(name, ip, user, password)
                        saved_connections = get_saved_connections()
                    except Exception as e:
                        print(f"\nError: {e}")
                        input("\nPress Enter to continue...")
                else:
                    print("\nConnection already exists.")
                    input("\nPress Enter to continue...")
            elif 1 <= choice <= len(saved_connections):
                id, name, ip, user, password = saved_connections[choice -1]
                try:
                        ssh_connect(ip, user, password)
                except Exception as e:
                    print(f"\nError: {e}")
                    input("\nPress Enter to continue...")
            else:
                    print("\nInvalid choice.")
                    input("\nPress Enter to continue...")

# Function to add the name column if it doesn't exist
def add_name_column():
    conn = sqlite3.connect('connections.db')
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE connections ADD COLUMN name TEXT')  # Add the new column
    except sqlite3.OperationalError as e:
        print("Error occurred while adding column:", e)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
