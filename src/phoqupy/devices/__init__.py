"""Device abstraction layer.

Hardware drivers are imported lazily inside ``connect()`` so that
``import phoqupy`` never requires any lab hardware or Windows-only libraries.
"""
