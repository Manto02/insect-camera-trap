# TODO
1) creare funzioni che salvi le immagini in una cartella e avere le immagini che contengono bene il timestamp
2) implementazione separate della funzione che applica l'inferenza sulle immagini in modo che possa essere un programma a se e tutto sia modulare e usabile separatamente a seconda delle esigenze
1) aumentare il framerate
2) argomento della soglia per il tracking al lancio
3) raggio della videocamera
4) cercare paper per capire come stimare l'area che hanno gli insetti
5) documentazione
6) se rimane tempo benchmark sulla rete (ethernet/wifi)

# at the moment
al momento il framerate e' salito e la soglia e' stata inserita come parametro ma ci sono problemi di prestazioni. Da pc 
fisso il framerate sta circa a 7 mentre da portatile oscilla tra 0.5 a 1.5. Probabilmente si potrebbe optare per non eseguire l' inferenza su tutti i frame ma solo dopo tot frame ricevuti in modo da alleggerire le operazioni eseguite dal programma.

- la visuale dentro la provette cilindrica in vetro funziona e il programma continua a rilevare gli insetti senza problemi

# range fotocamera
- allo stato attuale di focus:
  - distanza lente da terra: 4cm circa
  - larghezza immagine: 1.5 cm circa

- distanza con la lente al fuoco piu' lontano
  - distanza lente da terra: 6cm circa
  - larghezza immagine: 3 cm circa


# nuovi requisiti progetto
LE SPECIFICHE SONO IN DETTAGLIO SU GOOGLE KEEP
- possibile inferenza offline e non in diretta col video
- creare funzione che salva le immagini in modo da creare un dataset per poi studiare come fare l' inferenza con gli insetti in movimento

# domande entomologo
- velocita' insetti (media, frequenza di movimento...)
- gli insetti si sovrappongono?
- stima del tempo di un dataset (minuti, ore, giorni)
- 