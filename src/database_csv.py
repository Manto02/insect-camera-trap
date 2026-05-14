import csv
import os
import math

CSV_FILE_NAME = "../data/insect_tracking_log.csv"
CSV_HEADEARS = ["Insect_ID", "Center_X_Pixel", "Center_Y_Pixel", "Area_Pixel", "Timestamp"]
# Dizionario per memorizzare l'ultima posizione loggata per ogni insetto
_last_logged_centroids = {}


def _calculate_distance_pixels(p1, p2):
    if p1 is None or p2 is None:
        return 0.0
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# crea se non esiste il file csv per memorizzare i dati. Se esiste lo apre solamente
def initialize_csv(file_name = CSV_FILE_NAME):
    global LAST_X
    global LAST_Y
    global CSV_FILE_NAME
    CSV_FILE_NAME = file_name
    try:
        file_exists = False
        if os.path.exists(CSV_FILE_NAME):
            if os.stat(CSV_FILE_NAME).st_size > 0:
                file_exists = True
        
        with open(CSV_FILE_NAME, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(CSV_HEADEARS)
                print(f"Creato il file csv: {CSV_FILE_NAME} con intestazione {CSV_HEADEARS}")
            else:
                print(f"Apertura del file csv {CSV_FILE_NAME}")
    except IOError as e:
        print(f"Errore nell'inizializzione del file csv: {e}")
    except Exception as e:
        print(f"Errore nella creazione o apertura del file {CSV_FILE_NAME}: {e}")


# prende i dati li elabora e scrive dentro al file csv
def log_insect_data(insect_id, current_centroid, bbox, time, THRESHOLD_MOVEMENT):
    global _last_logged_centroids
    xmin, ymin, xmax, ymax = bbox
    
    #valutazione validita dello spostamento 
    last_logged_position = _last_logged_centroids.get(insect_id)
    movement_from_last_log = _calculate_distance_pixels(current_centroid, last_logged_position)
    if last_logged_position is None or movement_from_last_log >= THRESHOLD_MOVEMENT:
        # calcolo area della bounding box 
        width = xmax - xmin
        height = ymax - ymin
        area = width * height
        
        # forma dei dati richesta dall'intestazione del file csv
        row_data = [insect_id, current_centroid[0], current_centroid[1], area, time]
        print(f"I dati che verranno scritti sul csv sono:\n{row_data}\n")

        # scrittura della riga sul file csv
        try:
            with open(CSV_FILE_NAME, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(row_data)
            
            # aggiorno l'ultima posizione rilevata dentro al dizionario
            _last_logged_centroids[insect_id] = current_centroid

        except IOError as e:
            print(f"Errore durante l'apertura o scrittura del file: {e}")
        except Exception as e:
            print(f"Errore nel logging dei dati: {e}")
    else:
        print(f"Movimento per insetto_id({insect_id}) di {movement_from_last_log} inferiore alla soglia {THRESHOLD_MOVEMENT} e quindi non loggata")



if __name__ == "__main__":
    print(f"Dati contenuti del file {CSV_FILE_NAME}:")



    