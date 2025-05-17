import socket
import cv2
import time
from picamera2 import Picamera2
import numpy as np
import os
import sys
import tkinter


def get_screen_resolution_tkinter():
    """Ottiene la risoluzione dello schermo usando tkinter.
    Restituisce una tupla (larghezza, altezza) in pixel."""
    root = tkinter.Tk()
    root.withdraw()  # Nasconde la finestra principale di tkinter
    larghezza = root.winfo_screenwidth()
    altezza = root.winfo_screenheight()
    print(f"la risoluzione dello schermo e' {larghezza}x{altezza}")
    return larghezza, altezza


def send_frame_to_server(host, port):
    """
    Cattura frame dalla Raspberry Pi Camera e li invia a un server TCP.

    Args:
        host (str): L'indirizzo IP o hostname del server.
        port (int): La porta su cui il server e' in ascolto.
    """
    # Dimensioni del frame (puoi modificarle se necessario)
    resW, resH = get_screen_resolution_tkinter()

    # Inizializza picamera2
    picam2 = Picamera2()
    # Configura la camera. RGB format ha 3 canali.
    picam2.configure(
        picam2.create_video_configuration(
            main={"format": "XRGB8888", "size": (resW, resH)}
        )
    )
    picam2.start()

    print(f"Tentativo di connessione al server su {host}:{port}")

    # creazione socket e connessione
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((host, port))
        print(f"connesso al server {host}:{port}")

        # Inizializza la variabile per tenere traccia del tempo
        previous_time = time.time()
        capture_interval = 3  # Cattura un'immagine ogni n secondi

        while True:
            # Ottieni il tempo corrente
            current_time = time.time()
            time_elapsed = current_time - previous_time

            # Verifica se e' passato l'intervallo di cattura
            if time_elapsed >= capture_interval:
                # Acquisisci un frame dalla camera
                frame_bgra = picam2.capture_array()
                frame = cv2.cvtColor(
                    np.copy(frame_bgra), cv2.COLOR_BGRA2BGR
                )  # Rimuovi il canale alfa

                

                # --- Inizio logica invio frame ---
                # Codifica il frame come immagine JPEG
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
                    response = client_socket.recv(1024) # Riceve fino a 1024 byte di risposta
                    print(f"messaggio ricevuto: {response.decode('utf-8')}")
            
                    # Invia i byte dell'immagine
                    client_socket.sendall(image_bytes)
                    response = client_socket.recv(1024) # Riceve fino a 1024 byte di risposta
                    print(f"messaggio ricevuto: {response.decode('utf-8')}")
                    

                except socket.error as e:
                    print(f"Errore durante l'invio/ricezione dei dati: {e}")
                    break  # Esci dal loop in caso di errore di socket
                # --- Fine logica invio frame ---

                # Aggiorna il tempo precedente
                previous_time = current_time

       

    except ConnectionRefusedError:
        print(
            f"Errore: connessione rifiutata. Assicurati che il server sia in esecuzione su {host}:{port}"
        )
    except Exception as e:
        print(f"Errore durante la comunicazione col server: {e}")

    finally:
        # Rilascia le risorse
        picam2.stop()
        picam2.close()
        # chiusura della connessione
        client_socket.close()
        print("Connessione chiusa")


if __name__ == "__main__":
    # dati del server
    HOST = "192.168.0.2"  # SOSTITUISCI CON L'INDIRIZZO IP DEL TUO SERVER
    PORT = 12345

    send_frame_to_server(HOST, PORT)