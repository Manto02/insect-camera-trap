# insect-camera-trap
## [ITA] guida all'installazione
per usufruire del programma insect-camera-trap sono necessari alcuni programmi e dipendenze esterne.

### Requisiti
- un sistema linux
- python
- miniconda
  - per installare anaconda seguire la guida all'installazione sul sito https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html
### Installazione dell'environment conda e dipendenze
una volta clonata la repository sul proprio sistema sarà necessario entrare nella directory clonata e creare un ambiente virtuale python con conda in modo da poter gestire tutte le dipendenze necessarie per il programma

Seguire i seguenti comandi per installare l'ambiente
```bash
conda env create -f environment_cpu.yml
# or if you have a nvidia gpu
conda env create -f environment_gpu.yml
```
se non sei sicuro su quale installare usa environment_cpu.yml che è l'environment più generico
### Avvio programma
una volta installati tutti i requisiti e creato l'ambiente virtuale con conda sei pronto per avviare il programma

1) avvia l'ambiente virtuale
```bash
conda activate prog-cpu
#or if you installed the nvidia version
conda activate prog
```
2) esegui il server e recupera dal terminale l'ip tramite print del programma (o ifconfig da terminale) per poterlo inserire nel client
3) avvio server con flag come parametro:
   - flag -s o --save come parametro all' avvio:
     - il server al posto di eseguire l' inferenza delle immagini live iniziera' a salvare tutti i frame in una cartella di nome (data_ora_minuti) in un percorso a nostra scelta modificabile a riga 368 del server
   - flag -l o --live come parametro all' avvio:
     - il server eseguira' l' inferenza su tutti i frame catturati dal raspberry in tempo reale
   - flag -t o --threshold
     - il server prendera il valore inserito dopo la flag come nuovo valore di soglia da superare per inserire nel database un nuovo movimento
     
4) esegui il client.py sul raspberry andando a **inserire a fine file l'indirizzo IP del server**


- ora e' possibile eseguire l' inferenza sul dataset ottenuto tramite il server con la flag -s facendo partire il programma detection.py
-   per fare in modo che l' inferenza avvenga sul dataset voluto e' necessario andare a modificare il codice a riga 107 inserendo il path della cartella che si vuole analizzare

---


## [ENG] installation guide
for setup the environment install anaconda on your machine and next use this command to install all the dependencies needed
```bash
conda env create -f environment_cpu.yml
# or if you have a nvidia gpu
conda env create -f environment_gpu.yml
```

after the installation you have to activate the environment
```bash
conda activate prog-cpu #or prog if you installed the other version
```
