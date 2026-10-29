"""Shared OCR line reconstruction used by the app and research scripts."""


def reconstruct_lines(detections):
    rows = []
    boxes = []

    for detection in detections:
        xs, ys = zip(*detection["polygon"])
        boxes.append({
            "left": min(xs),
            "top": min(ys),
            "right": max(xs),
            "bottom": max(ys),
            "text": detection["text"],
            "id": detection["id"],
        })

    for box in sorted(boxes, key=lambda b: (b["top"], b["left"])):
        row = next((
            row for row in rows
            if (
                min(row["bottom"], box["bottom"])
                - max(row["top"], box["top"])
            ) >= 0.5 * min(
                row["bottom"] - row["top"],
                box["bottom"] - box["top"],
            )
        ), None)

        if row is None:
            rows.append({**box, "parts": [box]})
        else:
            row["parts"].append(box)
            row["top"] = min(row["top"], box["top"])
            row["bottom"] = max(row["bottom"], box["bottom"])

    lines = []

    for row in sorted(rows, key=lambda row: row["top"]):
        parts = sorted(row["parts"], key=lambda part: part["left"])
        lines.append({
            "text": " ".join(part["text"] for part in parts),
            "detection_ids": [part["id"] for part in parts],
        })

    return lines
