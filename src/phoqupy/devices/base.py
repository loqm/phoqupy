import importlib


def try_import(name):
    """Return the module if importable, else None (never raises)."""
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def resolve_simulate(simulate, *driver_modules):
    """Decide whether to simulate.

    If ``simulate`` is explicitly True/False, respect it. If None, auto-detect:
    simulate when any required driver is missing.
    """
    if simulate is not None:
        return bool(simulate)
    return any(try_import(m) is None for m in driver_modules)


class DeviceError(RuntimeError):
    pass
