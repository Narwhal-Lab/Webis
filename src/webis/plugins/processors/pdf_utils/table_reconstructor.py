import numpy as np
from sklearn.cluster import AgglomerativeClustering
from typing import List, Dict


class PDFTableReconstructor:


    def __init__(
        self,
        row_distance_threshold: float = 8.0,
        col_distance_threshold: float = 15.0,
    ):
        self.row_threshold = row_distance_threshold
        self.col_threshold = col_distance_threshold

    def reconstruct(self, blocks: List[Dict]) -> List[List[str]]:

        if not blocks:
            return []

        y_centers = np.array([
            [(b["top"] + b["bottom"]) / 2.0] for b in blocks
        ])

        row_cluster = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.row_threshold,
            linkage="single"
        ).fit(y_centers)

        x_centers = np.array([
            [(b["x0"] + b["x1"]) / 2.0] for b in blocks
        ])

        col_cluster = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.col_threshold,
            linkage="single"
        ).fit(x_centers)

        table_map = {}
        for block, r_label, c_label in zip(
            blocks, row_cluster.labels_, col_cluster.labels_
        ):
            table_map.setdefault(r_label, {})
            table_map[r_label].setdefault(c_label, [])
            table_map[r_label][c_label].append(block["text"])

        table: List[List[str]] = []
        for r in sorted(table_map.keys()):
            row_cells = []
            for c in sorted(table_map[r].keys()):
                cell_text = "".join(table_map[r][c])
                row_cells.append(cell_text)
            table.append(row_cells)

        return table
