"""
Image stitching module
Stitches multiple recognized images into a collage
"""
import cv2
import numpy as np
from datetime import datetime as dt


def add_to_stitching_dict(stitching_dict, img_id, conf_level, frame):
    """
    Add recognized image to stitching dictionary
    If the same image ID already has a higher-confidence image, do not update
    
    Args:
        stitching_dict: Dictionary storing images {img_id: (confidence, frame)}
        img_id: Image ID
        conf_level: Confidence level
        frame: Image frame
    """
    if img_id not in stitching_dict or (
        stitching_dict[img_id][0] < conf_level
    ):
        # If the newly detected confidence level > current one in the dictionary, replace
        stitching_dict[img_id] = (
            conf_level,
            frame,
        )
        print(f"Saw {img_id} with confidence level {conf_level}.")


def stitch_images(id_arr, stitching_dict, filename="task"):
    """
    Stitch recognized images into a tiled collage with labels.
    
    Each tile shows the bounding-box-annotated image with an
    "Obstacle N" label at the top.  Tiles are arranged in a grid
    (up to 2 rows), left-to-right in the order given by id_arr.
    
    Args:
        id_arr: Array of obstacle IDs, stitched in order
        stitching_dict: Dictionary storing images {obstacle_id: (confidence, frame)}
        filename: Output file name prefix
    """
    import math

    TILE_SIZE = 320
    LABEL_H = 30  # height of the label bar above each tile
    blank = np.zeros((TILE_SIZE + LABEL_H, TILE_SIZE, 3), np.uint8)

    n = len(id_arr)
    if n == 0:
        print("No images to stitch")
        return

    # Grid layout: 2 rows, ceil(n/2) columns
    n_cols = math.ceil(n / 2)
    n_rows = 2

    tiles = []
    for obs_id in id_arr:
        if obs_id not in stitching_dict:
            tiles.append(blank.copy())
            continue

        conf, img = stitching_dict[obs_id]
        img = cv2.resize(img, (TILE_SIZE, TILE_SIZE))

        # Add label bar on top
        label_bar = np.zeros((LABEL_H, TILE_SIZE, 3), np.uint8)
        text = f"Obstacle {obs_id} ({conf:.2f})"
        cv2.putText(label_bar, text, (5, 22),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                     cv2.LINE_AA)
        tile = np.vstack([label_bar, img])
        tiles.append(tile)

    # Pad to fill the grid
    while len(tiles) < n_rows * n_cols:
        tiles.append(blank.copy())

    # Assemble grid: stack columns, then hstack
    cols = []
    for c in range(n_cols):
        col_tiles = [tiles[c * n_rows + r] for r in range(n_rows)]
        cols.append(np.vstack(col_tiles))
    canvas = np.hstack(cols)

    # Save collage
    timestamp = dt.strftime(dt.now(), '%H%M%S')
    output_file = f"{filename}_collage_{timestamp}.jpg"
    cv2.imwrite(output_file, canvas)
    print(f"Collage saved as {output_file}")

    # Display collage
    window_name = "Task 2 — Recognized Images"
    cv2.imshow(window_name, canvas)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
