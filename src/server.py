import socket
import threading
import cv2
import numpy as np
import time
import argparse
import struct
import queue
import sys
from ultralytics import YOLO 
from proximity_tracker import ProximityTracker
from database_csv import *
from detection import inference_and_tracking
import tkinter as tk
from tkinter import filedialog

# creazione di una coda per gestire la visualizzazione dei frame fuori dal thread client
frame_queue = queue.Queue(maxsize=10) #maxsize=1 mostra solo il frame piu' recenteo
frame_with_detection_queue = queue.Queue(maxsize=10)
image_queue = queue.Queue(maxsize=50)

# evento thread per segnalare ai thread di terminare
stop_threads = threading.Event()

# variabili globali per il framerate
prev_frame_time = 0
THRESHOLD_MOVEMENT = 5.0 # soglia di pixel per il quale e' considerato valido uno spostamento dell'insetto e non un semplice reset della box
frames_directory = ""
save_flag = False
live_flag = False


def get_ip():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # connessione al server DNS di google per trovare ip di rete
        ip_address = s.getsockname()[0]
        return ip_address
    except Exception as e:
        print(f"Errore nel recupero dell'IP locale: {e}")
        # Fallback a localhost se non riesce a trovare un IP di rete
        return "127.0.0.1"
    finally:
        if s:
            s.close()


def loadYoloModel(yolo_model):
    try:
        model_path = "../yolo-models/insect_detect2.pt"
        yolo_model = YOLO(model_path, task = 'detect')
        print("Modello yolo caricato con successo")
        return yolo_model
    except Exception as e:
        print(f"Errore nel caricamento del modello yolo: {e}")
        print("Il server continuera' a ricevere le immagini ma non vi applichera' l' inferenza")
        yolo_model = None
        return yolo_model

def framerate():
    global prev_frame_time
    new_frame_time = time.time()
    print(f"new frame time: {new_frame_time}\nprev frame time: {prev_frame_time}")
    time_diff = new_frame_time - prev_frame_time
    
    if time_diff > 0:
        fps = 1 / time_diff
        fps_text = f"FPS: {fps:.2f}"
    else:
        fps_text = "FPS: N/A"
    
    prev_frame_time = new_frame_time
    
    return fps_text

def get_frame(client_socket, client_port):
    # dimensione prestabilita uguale a quella del client, indica la dimensione in byte (ex. 4) che conterranno il dato image_size
    image_size_bytes = 4
    try:
        while not stop_threads.is_set():
            size_data = b''
            # Ricevi dati dal client
            while len(size_data) < image_size_bytes:
                if stop_threads.is_set():
                    return
                try:
                    # timeout per evitare blocchi se il client di disconnette bruscamente
                    client_socket.settimeout(0.1)   
                    packet = client_socket.recv(image_size_bytes - len(size_data))  # Riceve fino a 1024 byte
                except socket.timeout:
                    if stop_threads.is_set():
                        return
                    continue # riprova a ricevere se il timeout scade ma il thread non deve fermarsi
                except socket.error as e:
                    print(f"Errore socket durante la ricezione della dimensione dell' immagine: {e}")
                    return
                        
                if not packet:
                    # Se non ci sono dati, il client si è disconnesso
                    print(f"Client {client_port} disconnesso durante la ricezione della dimensione dell'immagine.")
                    return

                size_data += packet
            try:
                #print(f"Ricevuti da {client_port} {len(size_data)} bytes per la dimensione dell'immagine")
                client_socket.sendall(b"Dimensioni immagine ricevuta")
            except socket.error as e:
                print(f"Errore socket durante l' invio di conferma della ricezione della dimensione dell' immagine: {e}")
                return

            # fine ricezione pacchetti e inizio codifica dei byte ricevuti in intero
            image_size = struct.unpack('!I', size_data)[0]

            #print(f"Ricevuto da {client_port} la grandezza dell'immagine: {image_size} bytes")

            
            # ricezione bytes dell'immagine
            image_data = b''
            while len(image_data) < image_size:
                if stop_threads.is_set():
                    return
                try:
                    client_socket.settimeout(0.1) # imposta timeout per la ricezione dell' immagine
                    bytes_to_receive = min(image_size - len(image_data), 4096)
                    packet = client_socket.recv(bytes_to_receive)
                except socket.timeout:
                    if stop_threads.is_set():
                        return
                    continue # prova a continuare la ricezione se il thread non e' stato interrotto
                except socket.error as e:
                    print(f"Errore socket durante la ricezione dell' immagine: {e}")
                    return

                if not packet:
                    # Se non ci sono dati, il client si è disconnesso
                    print(f"Client {client_port} disconnesso durante la ricezione dell'immagine.")
                    return
                
                image_data += packet
            try:
                client_socket.sendall(b"Immagine ricevuta\n")
                print("Fine ricezione dell'immagine\nInizio decodifica...")
            except socket.error as e:
                print(f"Errore socket durante l' invio di conferma della ricezione dell' immagine: {e}")
                return


            # codifica dei byte ricevuti in immagine jpg
            # conversione bytes in array numpy
            np_array = np.frombuffer(image_data, dtype=np.uint8)
            if save_flag:
                try:
                    image_queue.put_nowait(image_data)
                except queue.Full:
                    try:
                        image_queue.get_nowait()  # rimuovi il frame piu' vecchio
                        image_queue.put_nowait(image_data)  # inserisci il nuovo frame
                    except queue.Full:
                        pass  # se ancora pieno, scarta il nuovo frame
                
            # decodifica array numpy in immagine jpeg 
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            if frame is not None:
                # se la coda e' piena, scarta il frame piu' vecchio
                try:
                    frame_queue.put_nowait(frame)
                    print(f"stato frame_queue in get_frame: {frame_queue.qsize()}/{frame_queue.maxsize} frames")
                except queue.Full:
                    try:
                        frame_queue.get_nowait()  # rimuovi il frame piu' vecchio
                        frame_queue.put_nowait(frame)  # inserisci il nuovo frame
                    except queue.Full:
                        pass  # se ancora pieno, scarta il nuovo frame
            else:
                print(f"Errore nella decodifica dell'immagine ricevuta da {client_port}")
            
                
    except Exception as e:
        print(f"Errore nel thread di ricezione frame da {client_port}: {e}")

    finally:
        # quando il thread getframe termina chiude il socket garantendo la chiusura solo una volta
        try:
            client_socket.close()
        except Exception as e:
            print(f"Errore nella chiusura del socket del client {client_port}: {e}")
            pass

    print("Thread di ricezione frame terminato")

def save_frame(image, timestamp, directory):

    if not directory or os.path.isdir(directory) == False:
        print("Directory non valida per il salvataggio dei frame")
        return

    datetime = time.strftime('%Y_%m_%d__%H:%M:%S', time.localtime(timestamp))
    milliseconds = f"{int((timestamp % 1) * 1000):03d}"
    filename = f"{datetime}_{milliseconds}.jpg"
    print(f"directory: {directory}\nfilename: {filename}\nmilliseconds: {milliseconds}\n")

    filepath = os.path.join(directory, filename)
    print(f"Salvataggio del frame in {filepath}...\n\n\n\n\n\n\n\n")

    try:
        with open(filepath, 'wb') as f:
            f.write(image)
            print(f"Frame salvato in {filepath}")
    except Exception as e:
        print(f"Errore nel salvataggio del frame in {filepath}: {e}")
    
    return 


def handle_client(client_socket, client_port, model, insect_tracker):
    """Gestisce la comunicazione con un singolo client."""
    print(f"Connessione effettuata da {client_port}")

    # lista per tenere traccia dei thread creati per la ricezione dei frame
    listeners_handler = threading.Thread(target=get_frame, args=(client_socket, client_port))
    listeners_handler.start()

    # thread per salvataggio frame ricevuti
    #save_handler = threading.Thread(target=save_frame, args=(image_queue, frames_directory))
    #save_handler.start()

    try:
        while not stop_threads.is_set():
            try:
                # caricamento frame nella coda per la visualizazzione
                frame = frame_queue.get_nowait()
                print(f"stato frame_queue in handle_client: {frame_queue.qsize()}/{frame_queue.maxsize} frames")
            except queue.Empty:
               if not listeners_handler.is_alive():
                   print(f"Thread di ricezione frame da {client_port} non e' piu' attivo, terminazione gestione client")
                   break
               continue 

            # salvataggio del frame ricevuto se l' opzione e' attivata
            if save_flag:
                timestamp = time.time()
                image = image_queue.get_nowait()
                save_frame(image, timestamp, frames_directory)

            # calcolo del framerate
            fps_text = framerate()

            # inferenza e tracking
            if live_flag:
                timestamp = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(time.time())) 
                frame_with_detection_queue.put_nowait(inference_and_tracking(frame, model, insect_tracker, timestamp, THRESHOLD_MOVEMENT))

            
    except Exception as e:
        print(f"Errore durante la gestione del client {client_port}: {e}")

    finally:
       # ci assicuriamo che il thread che riceve i frame sia terinato prima di uscirea da handle_client
        if listeners_handler.is_alive():
            print(f"Attesa terminazione thread di ricezione frame da {client_port}")
            listeners_handler.join(timeout=1.0) 
        print(f"Connessione con il client {client_port} terminata")


def start_server(host, port):

    global stop_threads
    yolo_model = None

    """Avvia il server TCP."""
    # Crea un socket TCP/IP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Associa il socket all'indirizzo e alla porta
    server_socket.bind((host, port))
    # Metti il socket in ascolto per connessioni in entrata
    server_socket.listen(5)  # Accetta fino a 5 connessioni in coda

    print(f"Server in ascolto su {host}:{port}")

    yolo_model = loadYoloModel(yolo_model)

    # lista per tenere traccia dei thread creati, 1 per ogni client connesso
    client_threads = []
    
    # creazione finestra con cv2
    window_name = "Frame ricevuto dal client"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # creazione dell' oggetto ProximityTracker
    insect_tracker = ProximityTracker(max_distance=70, max_missing_frames=10)

    try:

        while not stop_threads.is_set():
            # creazione thread client ad avvenuta connessione
            try:
                # Aspetta una connessione
                server_socket.settimeout(0.1) # Imposta un breve timeout su accept
                client_socket, client_port = server_socket.accept()
                server_socket.settimeout(None)


                # Avvia un nuovo thread per gestire la connessione del client
                client_handler = threading.Thread(
                    target=handle_client, args=(client_socket, client_port, yolo_model, insect_tracker)
                )
                client_handler.start()
                client_threads.append(client_handler)
            except socket.timeout:
                pass 
            except socket.error as e:
                if not stop_threads.is_set():
                    print(f"Errore durante l' accettazione della connesione da parte del client: {e}")
            
            # rimuovi i thread terminati dalla lista dei thread client
            client_threads = [t for t in client_threads if t.is_alive()]

            # gestione visualizzazione frame
            try:
                frame_to_display = frame_with_detection_queue.get_nowait()
                cv2.imshow(window_name, frame_to_display)
            except queue.Empty:
                pass # la coda e' vuota, non c'e' un nuovo frame da mostrare

            # chiusura finestra di visualizzazione frame
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Tasto 'q' premuto\nChiusura server...")
                stop_threads.set()
                break
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                print("La finestra e' stata chiusa\nChiusura server...")
                stop_threads.set
                break

    except KeyboardInterrupt:
        print("Interruzzione da tastiera\nChiusura server...")
        stop_threads.set()
    except Exception as e:
        print(f"Errore nel loop principale del server: {e}")
        stop_threads.set()

    finally:
        # chiusura socket server
        server_socket.close()
        print("Socket server chiuso")
        
        # attendi terminazione dei thread ancora in corso
        for thread in client_threads:
            thread.join(timeout=3) # attendi al massimo n secondi per thread
            if thread.is_alive():
                print(f"Attenzione thread {thread} ancora in esecuzione")

        # chiusura delle finestre opencv
        cv2.destroyAllWindows()
        print("Finestre opencv chiuse")
        print("Server chiuso")
        sys.exit(0)
            
def create_frames_directory(frames_directory):
    import os
    import time
    
    timestamp = time.strftime('%Y_%m_%d__%H_%M_%S', time.localtime(time.time()))

    frames_directory = os.path.join(frames_directory, timestamp)
    try:
        os.makedirs(frames_directory, exist_ok=True)
    except Exception as e: 
        print(f"Errore nella creazione della cartella per il salvataggio dei frame: {e}")
        exit(1)
    print(f"La cartella per il salvataggio dei frame e': {frames_directory}")
    
    return frames_directory


if __name__ == "__main__":

    HOST = get_ip()
    PORT = 12345  # Scegli una porta libera

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--threshold', type=float, default=5.0, help='Soglia di movimento in pixel per loggare i dati nel file csv')
    parser.add_argument('-s', '--save', action='store_true', help='Salva i frame ricevuti in una cartella locale')
    parser.add_argument('-l', '--live', action='store_true', help='Esegue inferenza e tracking in tempo reale sui frame ricevuti')
    parser.add_argument('-p', '--path', type=str, default='', help='Percorso della cartella dove salvare i frame')

    args = parser.parse_args()
    save_flag = args.save
    live_flag = args.live
    THRESHOLD_MOVEMENT = args.threshold
    print(f"Soglia di movimento impostata a {THRESHOLD_MOVEMENT} pixel")
    
    initialize_csv()
    if save_flag: 
        if args.path != '':
            print("Server in avvio con modalita' salvataggio frame attivata")
            frames_directory = create_frames_directory(args.path)
        else:
            print("Seleziona la cartella dove salvare i frame ricevuti")
            root = tk.Tk()
            root.withdraw()  # Nascondi la finestra principale
            selected_directory = filedialog.askdirectory(title="Seleziona la cartella dove salvare i frame ricevuti")
            if selected_directory:
                frames_directory = create_frames_directory(selected_directory)
            else:
                print("Nessuna cartella selezionata. Per avviare il server in modalita' salvataggio frame e' necessario selezionare una cartella.")
                exit(1)
            start_server(HOST, PORT)
    elif live_flag == True and save_flag == False:
        print("Server in avvio con modalita' inferenza e tracking in tempo reale attivata")
        start_server(HOST, PORT)
    else:
        print("Specificare almeno una modalita' tra salvataggio frame (-s) o inferenza e tracking in tempo reale (-l) per avviare il server")
        exit(1)
    
