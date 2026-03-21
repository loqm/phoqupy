def resolve_kwargs(kwargs, debug=False):
    resolved_kwargs = {}
    for k, v in kwargs.items():
        if (isinstance(v, int)) or (isinstance(v, float)) or (isinstance(v, bool)) or (v is None):
            resolved_kwargs[k] = v
        else: 
            parts = v.split(".") # e.g. "TrigMode.RisingEdge"
            obj = globals().get(parts[0], None) # here: obj = TrigMode
            if obj: 
                resolved_kwargs[k] = getattr(obj, parts[1], None) # here: obj.RisingEdge
            else: 
                if (debug): print(f"Warning: Could not resolve {v} for {k}")
    return resolved_kwargs