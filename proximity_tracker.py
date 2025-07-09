import math
import time
import copy

class ProximityTracker:
    """
    Tracker di oggetti basati sulla prossimita' dei centroindi delle bounding box.
    Assegna ID univoci agli oggetti tracciati
    """

    # costruttore
    def __init__(self, max_distance=50, max_missing_frames=3):
        """
        Costruttore della classe.

        Args:
             max_distance (int): distanza massima in pixel tra un centroide rilevato e un centroide gia' tracciato
                                 per considerarli lo stesso oggetto
             max_missing_frames (int): numero massimo di frame in cui un oggetto puo' essere assente prima che venga
                                       rimosso dal tracking
        """
        self.next_id = 0
        self.tracked_objects = {}
        self.max_distance = max_distance
        self.max_missing_frames = max_missing_frames

    def _get_centroid(self, bbox):
        """
        Calcola il centroide (x, y) di una bounding box.

        Args:
            bbox (tuple): Una tupla (xmin, ymin, xmax, ymax).

        Returns:
            tuple: Il centroide (cx, cy).
        """
        xmin, ymin, xmax, ymax = bbox

        cx = int((xmin + xmax) / 2)
        cy = int((ymin + ymax) / 2)

        return (cx, cy)

    def _calculate_distance(self, p1, p2):
        """
        Calcola la distanza euclidea tra due punti.

        Args:
            p1 (tuple): Primo punto (x1, y1).
            p2 (tuple): Secondo punto (x2, y2).

        Returns:
            float: La distanza euclidea.
        """
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
    
    def get_total_tracked_objects(self):
        return copy.deepcopy(self.tracked_objects)
    
    def update(self, new_detections_bboxes):
        """
        Prende in input la lista degli oggetti rilevati e aggiorna le tracce degli oggetti se ci sono state modifiche dalla rilevazione precedente.

        Args:
            new_detections_bboxes (list): Una lista di bounding box rilevate nel frame corrente.
                                          Ogni bbox è una tupla (xmin, ymin, xmax, ymax).

        Returns:
            list: Una lista di dizionari, dove ogni dizionario rappresenta un oggetto tracciato
                  nel frame corrente con il suo ID assegnato, bbox e centroide.
                  Formato: [{'id': int, 'bbox': (xmin, ymin, xmax, ymax), 'centroid': (cx, cy)}]
        """
        current_frame_tracked_objects = []
        
        # Calcola i centroidi per le nuove rilevazioni
        new_detections_with_centroids = []
        for bbox in new_detections_bboxes:
            new_detections_with_centroids.append({'bbox': bbox, 'centroid': self._get_centroid(bbox)})

        # Mappa per tenere traccia delle rilevazioni e tracce già accoppiate in questo frame
        matched_new_detection_indices = set()
        matched_tracked_ids = set()

        # Fase 1: Prova ad accoppiare le nuove rilevazioni con gli oggetti tracciati esistenti
        for new_idx, new_det in enumerate(new_detections_with_centroids):
            min_dist = float('inf')
            best_match_id = None

            for tracked_id, tracked_obj in self.tracked_objects.items():
                if tracked_id in matched_tracked_ids: # Salta le tracce già accoppiate
                    continue

                dist = self._calculate_distance(new_det['centroid'], tracked_obj['last_position'])

                if dist < min_dist and dist < self.max_distance:
                    min_dist = dist
                    best_match_id = tracked_id

            if best_match_id is not None:
                # Aggiorna la traccia esistente
                self.tracked_objects[best_match_id]['last_position'] = new_det['centroid']
                self.tracked_objects[best_match_id]['frames_since_last_seen'] = 0
                self.tracked_objects[best_match_id]['bbox'] = new_det['bbox']
                self.tracked_objects[best_match_id]['last_seen_timestamp'] = time.time()
                current_frame_tracked_objects.append({
                    'id': best_match_id,
                    'bbox': new_det['bbox'],
                    'centroid': new_det['centroid']
                })
                matched_new_detection_indices.add(new_idx)
                matched_tracked_ids.add(best_match_id)

        # Fase 2: Gestisci le nuove rilevazioni non accoppiate (sono nuovi oggetti)
        for new_idx, new_det in enumerate(new_detections_with_centroids):
            if new_idx not in matched_new_detection_indices:
                new_id = self.next_id
                self.next_id += 1
                self.tracked_objects[new_id] = {
                    'last_position': new_det['centroid'],
                    'frames_since_last_seen': 0,
                    'bbox': new_det['bbox'],
                    'last_seen_timestamp': time.time()
                }
                current_frame_tracked_objects.append({
                    'id': new_id,
                    'bbox': new_det['bbox'],
                    'centroid': new_det['centroid']
                })

        # Fase 3: Aggiorna il contatore per le tracce esistenti non accoppiate e pulisci quelle vecchie
        ids_to_remove = []
        for tracked_id, tracked_obj in self.tracked_objects.items():
            if tracked_id not in matched_tracked_ids:
                tracked_obj['frames_since_last_seen'] += 1
                if tracked_obj['frames_since_last_seen'] > self.max_missing_frames:
                    ids_to_remove.append(tracked_id)
        
        for tracked_id in ids_to_remove:
            print(f"Rimossa traccia ID {tracked_id} (non vista per {self.max_missing_frames} frames).")
            del self.tracked_objects[tracked_id]

        return current_frame_tracked_objects

