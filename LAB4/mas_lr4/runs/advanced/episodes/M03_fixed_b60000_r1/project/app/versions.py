def record(doc, text):
    if doc["text"] == text:
        return
    doc["version"] += 1
    doc["text"] = text
    doc["history"].append({"version": doc["version"], "text": text})
