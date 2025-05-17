import socket
import cv2
import time
from picamera2 import Picamera2
import numpy as np
import os
import sys
import tkinter


def send_frame_to_server(host, port):
    """
    Cattura frame dalla Raspberry Pi Camera e li invia a un server TCP.

    Args:
        host (str): L'indirizzo IP o hostname del server.
        port (int): La porta su cui il server è in ascolto.
    """
    print(f"Tentativo di connessione al server su {host}:{port}")

    # creazione socket e connessione
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((host, port))
        print(f"connesso al server {host}:{port}")
        percorso_immagine = "./immagini_rilevate/prova.jpg"

        while True:

            frame = cv2.imread(percorso_immagine)
            ret, encoded_image = cv2.imencode(".jpg", frame)

            if not ret:
                print("Errore: Impossibile codificare l'immagine.")
                time.sleep(0.1)
                continue

            # Converti l'immagine codificata in byte
            image_bytes = encoded_image.tobytes()

            # Ottieni la dimensione dei byte dell'immagine
            image_size = len(image_bytes)

            try:
                # Invia la dimensione dell'immagine al server (come intero di 4 byte)
                client_socket.sendall(image_size.to_bytes(4, "big"))
                # Invia i byte dell'immagine
                client_socket.sendall(image_bytes)
                # print(f"Inviato frame di dimensione {image_size} bytes.")

                # eventuale risposta dal server (se il server invia una risposta)
                # response = client_socket.recv(1024) # Riceve fino a 1024 byte di risposta
                # print(f"messaggio ricevuto: {response.decode('utf-8')}")

            except socket.error as e:
                print(f"Errore durante l'invio/ricezione dei dati: {e}")
                break  # Esci dal loop in caso di errore di socket
            # --- Fine logica invio frame ---

    except ConnectionRefusedError:
        print(
            f"Errore: connessione rifiutata. Assicurati che il server sia in esecuzione su {host}:{port}"
        )
    except Exception as e:
        print(f"Errore durante la comunicazione col server: {e}")

    finally:
        # chiusura della connessione
        client_socket.close()
        print("Connessione chiusa")


if __name__ == "__main__":
    # dati del server
    HOST = "192.168.0.2"  # SOSTITUISCI CON L'INDIRIZZO IP DEL TUO SERVER
    PORT = 12345

    send_frame_to_server(HOST, PORT)
