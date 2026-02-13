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
    Stitch multiple images into a collage
    
    Args:
        id_arr: Array of image IDs, stitched in order
        stitching_dict: Dictionary storing images {img_id: (confidence, frame)}
        filename: Output file name prefix
    """
    col_count = 0

    blank = np.zeros((320, 320, 3), np.uint8)
    cols = []
    col_cur = []
    for id in id_arr:
        _, img = stitching_dict[id]
        img = cv2.resize(img, (320, 320))
        col_cur.append(img)
        col_count += 1

        if col_count == 2:
            col_count = 0
            cols.append(np.vstack(col_cur))
            col_cur.clear()
    
    rem = len(col_cur)
    if rem > 0 and rem < 2:
        col_cur.append(blank)
        cols.append(np.vstack(col_cur))
    canvas = np.hstack(cols)

    # Save collage and save a copy
    timestamp = dt.strftime(dt.now(), '%H%M%S')
    output_file = f"{filename}_collage_{timestamp}.jpg"
    cv2.imwrite(output_file, canvas)
    print(f"Collage saved as {output_file}")

    # Display collage
    window_name = "collage: " + filename
    cv2.imshow(window_name, canvas)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
