class Quota:
    def __init__(self, store):
        self.store = store

    def size(self, text):
        return len(text)

    def usage(self, tenant):
        return sum(self.size(d["text"]) for d in self.store.state["docs"].values()
                   if d["tenant"] == tenant and not d["deleted"])

    def fits(self, tenant, text, old_text=""):
        return self.usage(tenant) - self.size(old_text) + self.size(text) <= self.store.tenants[tenant]
