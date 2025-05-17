import socket
import threading
import cv2
import numpy as np
import struct
import queue
import sys

# creazione di una coda per gestire la visualizzazione dei frame fuori dal thread client
frame_queue = queue.Queue(maxsize=100) #maxsize=1 mostra solo il frame piu' recente

# flag per segnalare ai thread di terminare
stop_threads = False


def handle_client(client_socket, client_port):
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

            client_socket.sendall(b"Immagine ricevuta")
            print("Fine ricezione dell'immagine\nInizio decodifica...")


            # codifica dei byte ricevuti in immagine jpg
            # conversione bytes in array numpy
            np_array = np.frombuffer(image_data, dtype=np.uint8)
            # decodifica array numpy in immagine jpeg 
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            
            # visualizzazione frame ricevuto
            if frame is not None:
                try:
                    frame_queue.put_nowait(frame)
                    print(f"Numero di frame all' interno della coda: {frame_queue.qsize}")
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

    """Avvia il server TCP."""
    # Crea un socket TCP/IP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Associa il socket all'indirizzo e alla porta
    server_socket.bind((host, port))
    # Metti il socket in ascolto per connessioni in entrata
    server_socket.listen(5)  # Accetta fino a 5 connessioni in coda

    print(f"Server in ascolto su {host}:{port}")

    # lista per tenere traccia dei thread creati
    client_threads = []
    
    # creazione finestra con cv2
    window_name = "Frame ricevuto dal client"
    #cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            try:
                # Aspetta una connessione
                server_socket.settimeout(0.1) # Imposta un breve timeout su accept
                client_socket, client_port = server_socket.accept()
                server_socket.settimeout(None)


                # Avvia un nuovo thread per gestire la connessione del client
                client_handler = threading.Thread(
                    target=handle_client, args=(client_socket, client_port)
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
                print("La coda e' vuota")
                pass # la coda e' vuota, non c'e' un nuovo frame da mostrare

            # chiusura finestra di visualizzazione frame
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Tasto 'q' premuto\nChiusura server...")
                stop_threads = True
                break
            # if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            #     print("La finestra e' stata chiusa\nChiusura server...")
            #     stop_threads = True
            #     break
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

    #HOST = socket.gethostbyname(socket.gethostname())
    HOST = "192.168.0.2"
    PORT = 12345  # Scegli una porta libera

    start_server(HOST, PORT)
