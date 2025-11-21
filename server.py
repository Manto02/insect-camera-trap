import socket
import threading
import cv2
import numpy as np
import time
import struct
import queue
import sys
from ultralytics import YOLO 
from proximity_tracker import ProximityTracker
from database_csv import *

# creazione di una coda per gestire la visualizzazione dei frame fuori dal thread client
frame_queue = queue.Queue() #maxsize=1 mostra solo il frame piu' recente

# flag per segnalare ai thread di terminare
stop_threads = False

# variabili globali per il framerate
prev_frame_time = 0


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
        model_path = "./yolo-models/insect_detect2.pt"
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

def handle_client(client_socket, client_port, model, insect_tracker):
    """Gestisce la comunicazione con un singolo client."""
    print(f"Connessione accettata da {client_port}")

    # dimensione prestabilita uguale a quella del client, indica la dimensione in byte (ex. 4) che conterranno il dato image_size
    image_size_bytes = 4

    try:
        while not stop_threads:
            size_data = b''
            # Ricevi dati dal client
            while len(size_data) < image_size_bytes:
                if stop_threads:
                    break
                try:
                    # timeout per evitare blocchi se il client di disconnette bruscamente
                    client_socket.settimeout(1.0) # timeout 1 secondo    
                    packet = client_socket.recv(image_size_bytes - len(size_data))  # Riceve fino a 1024 byte
                except socket.timeout:
                    if stop_threads:
                        break
                    continue # riprova a ricevere se il timeout scade ma il thread non deve fermarsi
                except socket.error as e:
                    print(f"Errore socket durante la ricezione della dimensione dell' immagine: {e}")
                    break
                     
                if not packet:
                    # Se non ci sono dati, il client si è disconnesso
                    print(f"Client {client_port} disconnesso durante la ricezione della dimensione dell'immagine.")
                    break

                size_data += packet
            
            client_socket.sendall(b"Dimensioni immagine ricevuta")

            # fine ricezione pacchetti e inizio codifica dei byte ricevuti in intero
            image_size = struct.unpack('!I', size_data)[0]

            print(f"Ricevuto da {client_port} la grandezza dell'immagine: {image_size} bytes")

            
            # ricezione bytes dell'immagine
            image_data = b''
            while len(image_data) < image_size:
                if stop_threads:
                    break
                try:
                    # imposta timeout per la ricezione dell' immagine
                    client_socket.settimeout(1.0)
                    bytes_to_receive = min(image_size - len(image_data), 4096)
                    #print(f"la dimensione attuale di image_data: {len(image_data)} < {image_size}")
                    packet = client_socket.recv(bytes_to_receive)
                except socket.timeout:
                    if stop_threads:
                        break
                    continue # prova a continuare la ricezione se il thread non e' stato interrotto
                except socket.error as e:
                    print(f"Errore socket durante la ricezione dell' immagine: {e}")
                    break

                if not packet:
                    # Se non ci sono dati, il client si è disconnesso
                    print(f"Client {client_port} disconnesso durante la ricezione dell'immagine.")
                    break
                image_data += packet

            client_socket.sendall(b"Immagine ricevuta\n")
            print("Fine ricezione dell'immagine\nInizio decodifica...")


            # codifica dei byte ricevuti in immagine jpg
            # conversione bytes in array numpy
            np_array = np.frombuffer(image_data, dtype=np.uint8)
            # decodifica array numpy in immagine jpeg 
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            
            # calcolo del framerate
            fps_text = framerate()

            # caricamento frame nella coda per la visualizazzione
            if frame is not None:
                try:
                    # inferenza yolo 
                    if model is not None:
                        results = model.predict(frame, verbose=False)
                        frame_with_detection = frame.copy()

                        # recupero delle coordinate delle bounding boxes
                        objects_detected_boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                        

                        # tracking degli oggetti rivelati e attribuzione id di tracking
                        total_tracked_objects = insect_tracker.get_total_tracked_objects()
                        print(f"total tracked objects:\n{total_tracked_objects}")
                        tracked_objects_in_frame = insect_tracker.update(objects_detected_boxes)

                        
                        # disegna le informazioni sul frame e salva i log su un file csv
                        for obj in tracked_objects_in_frame:
                            id = obj['id']
                            bbox = obj['bbox']
                            xmin, ymin, xmax, ymax = bbox
                            centroid = obj['centroid']
                            if id in total_tracked_objects:
                                prev_centroid = total_tracked_objects[id]['last_position']
                            else:
                                prev_centroid = (0,0)
                            print(f"centroide: {centroid}, prev centroid: {prev_centroid}")
                            current_time = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(time.time()))
                           
                            # stampa il timestamp
                            cv2.putText(frame_with_detection, current_time, (frame_with_detection.shape[1] - 270, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                            #stampa il framerate
                            cv2.putText(frame_with_detection, fps_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA) 
                            # disegna bounding box
                            cv2.rectangle(frame_with_detection, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                            # disegna il centroide
                            cv2.circle(frame_with_detection, centroid, 5, (0, 0, 255), -1) 
                            # scrive ID
                            cv2.putText(frame_with_detection, f"ID: {id}", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2, cv2.LINE_AA)

                            # salvataggio del log sul file csv come database
                            log_insect_data(id, centroid, bbox, current_time)
                            

                        frame_queue.put_nowait(frame_with_detection)
                        print(f"Inserito nella coda un frame con detenzione del modello caricato\n")
                    else:
                        frame_queue.put_nowait(frame)
                        print("Inserimento nella coda di un frame senza detenzioni")
                    
                except queue.Full:
                    print("La coda e' piena")
                    pass # la coda e' piena e il frame viene scartato
            else:
                print(f"errore nella decodifica dell'immagine da {client_port}")
            


    except Exception as e:
        print(f"Errore durante la gestione del client {client_port}: {e}")

    finally:
        # Chiudi la connessione con il client
        client_socket.close()
        print(f"Connessione con {client_port} chiusa.")


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

    # lista per tenere traccia dei thread creati
    client_threads = []
    
    # creazione finestra con cv2
    window_name = "Frame ricevuto dal client"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # creazione dell' oggetto ProximityTracker
    insect_tracker = ProximityTracker(max_distance=70, max_missing_frames=5)

    try:
        while True:
            try:
                # Aspetta una connessione
                server_socket.settimeout(1) # Imposta un breve timeout su accept
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
                print(f"Errore durante l' accettazione della connesione da parte del client: {e}")

            # gestione visuallizzazione frame
            try:
                frame_to_display = frame_queue.get_nowait()
                cv2.imshow(window_name, frame_to_display)
            except queue.Empty:
                pass # la coda e' vuota, non c'e' un nuovo frame da mostrare

            # chiusura finestra di visualizzazione frame
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Tasto 'q' premuto\nChiusura server...")
                stop_threads = True
                break
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                print("La finestra e' stata chiusa\nChiusura server...")
                stop_threads = True
                break
    except KeyboardInterrupt:
        print("Interruzzione da tastiera\nChiusura server...")
        stop_threads = True
    except Exception as e:
        print(f"Errore nel loop principale del server: {e}")
        stop_threads = True

    finally:
        # chiusura socket server
        server_socket.close()
        print("Socket server chiuso")
        
        # attendi terminazione dei thread ancora in corso
        for thread in client_threads:
            thread.join(timeout=1) # attendi al massimo 5 secondi per thread
            if thread.is_alive():
                print(f"Attenzione thread {thread} ancora in esecuzione")

        # chiusura delle finestre opencv
        cv2.destroyAllWindows()
        print("Finestre opencv chiuse")
        print("Server chiuso")
        sys.exit(0)
            


if __name__ == "__main__":

    HOST = get_ip()
    PORT = 12345  # Scegli una porta libera

    start_server(HOST, PORT)
