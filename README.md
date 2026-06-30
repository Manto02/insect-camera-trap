# Indice

## [1. Architettura del sistema](#1-architettura-del-sistema)

## [2. Setup ed installazione ambiente](#2-setup-ed-installazione-ambiente)

## [3. Guida all'avvio ed utilizzo](#3-guida-allavvio-ed-utilizzo-1) 

## [4. Struttura file](#4-struttura-file-1)

## [5. Addestramento modello di object detection YOLO](#5-addestramento-modello-di-object-detection-yolo-1)

## [6. Stato del progetto](#6-stato-del-progetto-1)




# 1. Architettura del sistema
Il sistema si basa su un architettura di tipo client-server accompagnata da un modello YOLO di computer vision che si occupa dell' inferenza e tracciamento degli insetti.

## Client
Il ruolo del client e' svolto da un raspberry pi 3b che tramite la sua fotocamera con obbiettivo macro acquisisce le immagini degli insetti e le spedisce al server tramite la rete. Le immagini vengono elaborate tramite un programma python (client.py) che usa come librerie principali opencv e picamera2 per trasformare le immagini in file jpg. Una volta ottenuta l'immagine viene spedita tramite protocollo TCP al server.

## Server
Il ruolo del server viene invece ricoperto da un computer piu' potente per permettere di analizzare le immagini ricevute dal client in live oppure in differita. Il server si occupa di aprire la connessione col client e a seconda della sua modalità di avvio procede a salvarsi le immagini in una cartella scelta dall'utente o eseguire direttamente il tracking live degli insetti tramite un modello YOLO che esegue l'inferenza sulle immagini ricevute tramite la rete.

# 2. Setup ed installazione ambiente
## requisiti di sistema
### hardware
Client:
- raspberry pi3 o superiore

Server:
- computer con linux

### software
L'intero progetto si basa su programmi scritti in python. Per facilitare lo sviluppo e le dipendenze il sistema usa come ambiente virtuale di sviluppo Anaconda.

- python 3.9.18 -> https://docs.python.org/release/3.9.18/
- miniconda -> guida all'installazione https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html
  
## installazione dipendenze
Con l'ausilio dell'ambiente virtuale di conda è possibile installare direttamente tutte le dipendenze e librerie richieste per il funzionamento usando il file di configurazione .yml a seconda dell'architettura video del server.
- environment_cpu.yml -> **file consigliato per uso generico** 
- environment_gpu.yml -> file da utilizzare solo se si è in possesso di un computer con scheda grafica nvidia e driver installati in linux

Una volta installato conda basterà eseguire il seguente comando per installare l'ambiente necessario
```bash
conda env create -f environment_cpu.yml
# or if you have a nvidia gpu
conda env create -f environment_gpu.yml
```

# 3. Guida all'avvio ed utilizzo
Una volta installato l'ambiente virtuale con tutte le sue dipendenze il progetto è pronto all'utilizzo.
## guida step by step per l'avvio
1. avviare l'ambiente virtuale di conda
```bash
conda activate prog-cpu
#or if you installed the nvidia version
conda activate prog
```
2. recupera dal terminale l'ip del server che servirà al client per connettersi
```bash
ifconfig 
```
3. avvia il server con i parametri e la modalità che vuoi usare

**PER AVVIARE IL SERVER È SEMPRE NECESSARIO SPECIFICARE UNA MODALITÀ DI UTILIZZO TRAMITE LA RELATIVA FLAG**

- flag -s o --save come parametro all' avvio:

    il server al posto di eseguire l' inferenza delle immagini live iniziera' a salvare tutti i frame in una cartella di nome (data_ora_minuti) in un percorso scelto all'avvio.
```bash
python3 server.py -s
```

- flag -l o --live come parametro all' avvio:

    il server eseguira' l' inferenza su tutti i frame catturati dal raspberry in tempo reale
```bash
python3 server.py -l
```

- flag -t o --threshold

    il server prende il valore inserito dopo la flag come nuovo valore di soglia da superare, per inserire nel database un nuovo movimento
```bash
python3 server.py -t  <your value> -s
# or
python3 server.py -t  <your value> -s
```
4. avvia il raspberry ed esegui il file client.py
```bash
python3 client.py -ip  <ip del server>
```

## inferenza su un dataset
Se abbiamo eseguito il server con la flag -s per salvare i frame ricevuti dal client, ora abbiamo a disposizione una cartella con un dataset da analizzare.

Per eseguire l'inferenza su un dataset usare il file detection.py
```bash
python3 detection.py 
```
una volta avviato il programma chiederà all'utente la cartella su cui vuole fare inferenza e salverà i dati ottenuti in un file csv dedicato

# 4. Struttura file

```bash
insect-camera-trap/
├── data/   # Cartella per log CSV e dati raccolti
│       └── insect_tracking_log.csv         # File di salvataggio per informazioni tracking
├── src/    # Sorgenti del progetto
│       ├── client.py                       # Cattura le immagini e le invia al server
│       ├── server.py                       # Riceve le immagini dal client e le elabora
│       ├── detection.py                    # Esegue inferenza immagini di un dataset 
│       ├── simple_tracker.py               # Logica di tracking e ID oggetti
│       └── csv_logger.py                   # Funzioni per la persistenza dati su CSV
├── yolo-models/    # Cartella che contiene i modelli pythorch per l'inferenza con YOLO
│       ├── insect_detect2.pt 
│       └── photos_insect_detect.pt   
├── environment_cpu.yml                 # File di configurazione principale ambiente virtuale ANACONDA
├── environment_gpu.yml                 # File di configurazione per driver nvidia di ANACONDA
└── README.md   # Documentazione principale
```

## server.py
il server si occupa di:
1. avviare la connessione TCP
2. caricare il modello YOLO per l'inferenza sulle immagini
3. gestire le connessioni coi client tramite thread
- se avviato in modalità live mostra il tracciamento in diretta con le bounding boxes intorno agli insetti rilevati

## client.py
Il client si trova sul raspberry e si occupa di:
1. connettersi al server
2. scattare le foto tramite picamera2 e elaborarle con opencv
3. inviare le foto al server

## proximity_tracker.py
Programma che esegue il tracciamento degli insetti individuati. Il programma viene richiamato dal Server per la creazione dell'oggetto ProximityTracker.
1. riceve una lista con gli insetti tracciati e i loro ID corrispettivi
2. ricava il centro di posizione dell'insetto
3. calcola il movimento, se c'è stato, tramite distanza euclidea
4. aggiorna la nuova posizione per l'insetto

Questo programma gestisce anche il rilevamento di nuovi insetti e anche la loro scomparsa dal campo visivo tramite un sistema di ID progressivi

## database_csv.py
Programma che si occupa di scrivere su un file csv i dati generati dall'inferenza sui frame, viene richiamato dal server per usare le sue funzioni.
1. genera un file csv o lo apre se già esistente
2. riceve in input una lista con ID insetto, posizione, tempo e soglia di movimento
3. se un insetto si è spostato dal sul vecchio record di una distanza maggiore della soglia di movimento allora il programma procede a registrare un nuovo record dell'insetto con tutti i dati sulla posizione e il tempo aggiornati

## detection.py
Questo programma viene richiamato dal Server per:
 - disegnare le informazioni ottenute dal proximity_tracker come le bounding boxes
 -  richiamare la funzione da database.csv per salvare i movimenti degli insetti

Questo programma viene anche usato dopo il server in modalità salvataggio (-s) oppure quando abbiamo già un cartella con un dataset da analizzare. 
detection.py prende le immagini di un dataset e le analizza tramite il modello YOLO allenato.
1. chiede la cartella contente il dataset
2. passa un frame alla volta al modello YOLO che effettua l'inferenza
3. scrive su un file csv i risultati del modello

# 5. Addestramento modello di object detection YOLO
## modello
Il modello di computer vision utilizzato per il tracking è YOLOv5, https://docs.ultralytics.com/models/yolov5#overview. È stato utilizzato YOLOv5 che è uno dei modelli meno potenti perchè inizialmente il progetto doveva essere interamente eseguito dal raspberry. Nonostante l'efficienza e leggerenza della versione 5 del modello YOLO le prestazioni dell'intero progetto sul raspberry pi3b erano scarse e quindi si è optato per un architettura di tipo client-server.

Per ottenere delle prestazioni migliori nel riconoscimento si può usare una versione più aggiornata di YOLO

## addestramento
Per il processo di addestramento ci sono 2 fasi principali.

È consigliato aiutarsi nel processo di addestramento con questo video tutorial che presenta tutte le fasi nel dettaglio con esempi.
https://www.youtube.com/watch?v=r0RspiLG260&t=16s

### 1. etichettatura delle immagini
per effettuare l'etichettatura di un dataset è stato usato un software apposito https://labelstud.io/

il software è molto semplice ed intuitivo e ci fornirà direttamente un dataset fatto per YOLO. 
Qualora fare l'etichettatura delle immagini con le boundig box dovesse dare problemi con il tracciamento degli insetti si può provare a ritagliare completamente gli insetti. Questo processo però è molto dispendioso.

### 2. allenamento del modello
per allenare il modello una volta recuperato il dataset etichettato è stato usato un tool gratuito di google.

link tool + tutorial: https://colab.research.google.com/github/EdjeElectronics/Train-and-Deploy-YOLO-Models/blob/main/Train_YOLO_Models.ipynb

È fortemente consigliato seguire passo passo il tutorial per allenare correttamente il modello.


# 6. Stato del progetto 
Il progetto è funzionante, ma non è stato testato sugli insetti in movimento, pertanto, nonostante la base del sistema di tracking sia funzionante, non sappiamo come si comporterà il sistema con gli insetti in movimento e di conseguenza non conosciamo la precisione del tracking e neanche la sua completa efficacia.

L'obbiettivo, quindi, è di testare il sistema in un ambiente di lavoro effettivo, in modo da poter costruire dei dataset con la modalità save del server e poter riallenare il modello coi dati raccolti e sistemare la soglia di movimento.

## limitazioni
- Il sistema TCP attuale non prevede una gestione robusta delle riconnessioni automatiche. In caso di caduta della rete, è necessario riavviare manualmente sia il server che il client

## TODO
- inserire metadati nei frame catturati dal raspberry
- provare il sistema di tracking in un ambiente di lavoro reale con insetti in movimento
  - gestire il valore di soglia per rendere i record di movimento realistici
  - gestire la vicinanza e sovrapposizione degli insetti
- aumentare il framerate per poterlo usare con anche altri insetti o animali
