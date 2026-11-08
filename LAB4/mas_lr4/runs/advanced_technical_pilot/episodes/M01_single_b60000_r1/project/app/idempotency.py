def is_duplicate(state, event):
    return event["id"] in state.seen


def finish(state, event, status):
    if status == "applied":
        state.seen.add(event["id"])
