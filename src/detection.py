import cv2
import numpy as np
import time
from ultralytics import YOLO 
from database_csv import *
import os
import argparse
from proximity_tracker import ProximityTracker
import tkinter as tk
from tkinter import filedialog

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

def get_ordered_image_files(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        print(f"Errore: La directory '{directory}' non esiste.")
        return []

    # Elenca tutti i file che terminano con .jpg (ignorando la case)
    image_files = [f for f in os.listdir(directory) if f.lower().endswith(('.jpg', '.jpeg'))]

    # Ordina i file per nome (che include il timestamp)
    image_files.sort()
    
    # Crea i percorsi completi
    full_paths = [os.path.join(directory, f) for f in image_files]
    
    return full_paths


def get_frame_timestamp(image_path):
    file_name = os.path.basename(image_path)
    timestamp_str = os.path.splitext(file_name)[0]  # Rimuove l'estensione
    return timestamp_str

    
def inference_and_tracking(frame, model, insect_tracker, frame_timestamp, THRESHOLD_MOVEMENT):
    if frame is not None:
        frame_with_detection = frame.copy()
        # inferenza yolo 
        if model is not None:
            results = model.predict(frame, verbose=False)

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
            
                # stampa il timestamp
                cv2.putText(frame_with_detection, frame_timestamp, (frame_with_detection.shape[1] - 270, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                # disegna bounding box
                cv2.rectangle(frame_with_detection, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                # disegna il centroide
                cv2.circle(frame_with_detection, centroid, 5, (0, 0, 255), -1) 
                # scrive ID
                cv2.putText(frame_with_detection, f"ID: {id}", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2, cv2.LINE_AA)

                # salvataggio del log sul file csv come database
                log_insect_data(id, centroid, bbox, frame_timestamp, THRESHOLD_MOVEMENT)
                    
        return frame_with_detection
    else:
        return frame

def main(image_directory: str):

    all_image_paths = get_ordered_image_files(image_directory)
    for image_path in all_image_paths:
        frame = cv2.imread(image_path)
        frame_timestamp = get_frame_timestamp(image_path)
        print(f"Processing image: {image_path} with timestamp: {frame_timestamp}")
        # esegui inferenza e tracking
        processed_frame = inference_and_tracking(frame, model, insect_tracker, frame_timestamp, THRESHOLD_MOVEMENT)
        # mostra il frame processato
        cv2.imshow("Insect Detection and Tracking", processed_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":

    # parser per argomenti da linea di comando
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--threshold', type=float, default=5.0, help='Soglia di movimento in pixel per loggare i dati nel file csv')
    parser.add_argument('-p', '--path', type=str, default="", help='Directory contenente le immagini da processare')
    args = parser.parse_args()
    THRESHOLD_MOVEMENT = args.threshold
    image_directory = args.path

    # creo o apro il csv per il logging dei dati
    initialize_csv("../data/prova_tracking_differita.csv")

    # carico il modello yolo
    model = loadYoloModel(None)
    
    # inizializzo il tracker
    insect_tracker = ProximityTracker(max_distance=70, max_missing_frames=10)

    print(f"Soglia di movimento impostata a {THRESHOLD_MOVEMENT} pixel")
    
    if image_directory == "":
        print("Nessuna directory specificata. Scegliere la directory contenente le immagini per procedere.")
        root = tk.Tk()
        root.withdraw()  # Nasconde la finestra principale
        selected_directory = filedialog.askdirectory(title="Seleziona la directory contenente le immagini")
        print(f"Directory selezionata: {selected_directory}")
        main(selected_directory)
    else:
        main(image_directory)