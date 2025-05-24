import math
import time


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

    def update(self, new_detections_bboxes):
        """
        Aggiorna le tracce degli oggetti con le nuove rilevazioni.

        Args:
            new_detections_bboxes (list): Una lista di bounding box rilevate nel frame corrente.
                                          Ogni bbox è una tupla (xmin, ymin, xmax, ymax).

        Returns:
            list: Una lista di dizionari, dove ogni dizionario rappresenta un oggetto tracciato
                  nel frame corrente con il suo ID assegnato, bbox e centroide.
                  Formato: [{'id': int, 'bbox': (xmin, ymin, xmax, ymax), 'centroid': (cx, cy)}]
        """
