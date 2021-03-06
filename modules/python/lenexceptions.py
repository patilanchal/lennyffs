# lenexceptions.py
# James Mithen
# j.mithen@surrey.ac.uk

"""
Exception classes used globally.  These are currently empty.
"""

# error with a utility (see util/ folder)
class UtilError(Exception): pass

# input parameter missing from file
class NoInputParamError(Exception): pass

# general input parameter error
class InputParamError(Exception): pass

# input parameter is not on an allowed list
class InputParamNotAllowedError(Exception): pass

# input parameter can't be converted properly
class InputParamUnconvertibleError(Exception): pass

# FFS error
class FFSError(Exception): pass
