def make_catalog(packages):
    catalog = {}
    for package in packages:
        catalog[package["name"]] = package
    return catalog


def alternatives(clause, catalog, forbidden):
    available = []
    for name in clause:
        if name in catalog and name not in forbidden:
            available.append(name)
    return sorted(set(available), key=lambda name: [catalog[name]["cost"], name])


def install_package(name, catalog, selected, forbidden, visiting):
    if name in visiting:
        return None
    if name in selected:
        return selected.copy()
    if name not in catalog or name in forbidden:
        return None
    package = catalog[name]
    for conflict in package["conflicts"]:
        if conflict in selected:
            return None
    working = selected.copy()
    working.add(name)
    path = visiting.copy()
    path.add(name)
    for clause in package["requires"]:
        if any(item in working and item not in path for item in clause):
            continue
        choice = None
        for item in alternatives(clause, catalog, forbidden):
            candidate = install_package(item, catalog, working, forbidden, path)
            if candidate is not None:
                choice = candidate
                break
        if choice is None:
            return None
        working = choice
    return working


def plan_cost(selected, catalog):
    total = 0
    for name in selected:
        total += catalog[name]["cost"]
    return total


def format_plan(selected, installed, catalog):
    added = []
    for name in sorted(selected):
        if name not in installed:
            added.append(name)
    return {
        "status": "ok",
        "cost": plan_cost(selected, catalog),
        "added": added,
        "selected": sorted(selected)
    }


def solve(data):
    catalog = make_catalog(data["packages"])
    installed = set(data["installed"])
    forbidden = set(data["forbidden"])
    for name in installed:
        if name not in catalog or name in forbidden:
            return {"status": "impossible"}
    selected = installed.copy()
    requested = sorted(set(data["requested"]))
    for name in requested:
        candidate = install_package(name, catalog, selected, forbidden, set())
        if candidate is None:
            return {"status": "impossible"}
        selected = candidate
    for name in selected:
        if name in forbidden:
            return {"status": "impossible"}
    return format_plan(selected, installed, catalog)
