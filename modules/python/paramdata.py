# paramdata.py
# James Mithen
# j.mithen@surrey.ac.uk

"""
Information on the allowed input parameters, and functions to convert
them from a string (as they are read in from the input file) to the
desired Python type.
"""

INT = 'int'
INTLIST = 'intlist'
FLOATLIST = 'floatlist'
FLOAT = 'float'
STRING = 'str'
BOOL = 'bool'

# parameter dictionary contains type info for all allowed parameters
# key is name of parameter, value is type, either string, float, int,
# or 'intlist'.  Here are example lines from a possible input ('in')
# file showing the different types:
# simulation new
# Tstar 0.45
# nlayersurf 3
# lambdas [10,20,30,40,50]

PDICT = {# simulation params
         'simulation': STRING,
         'restartfile': STRING,

         # interaction potential params
         'potential': STRING,
         'rcut': FLOAT,
         # for lennard-jones potential, these parameters control the
         # surface-fluid interaction potential scaling
         'r6mult': FLOAT,
         'r12mult': FLOAT,
         # for ipl (inverse power law potential), this controls the
         # exponent (it should be positive).
         'potexponent': FLOAT,

         # fluid params
         'nstar': FLOAT,
         'Tstar': FLOAT,
         'nparfl': INT,
         'rcinit': FLOAT,
         'pressure': FLOAT,

         # surface params
         'surface': BOOL,
         'surftype': STRING,
         'lxsurf': INT,
         'lysurf': INT,
         'nlayersurf': INT,
         'nlatt': FLOAT,
         'flinit': STRING,
         'nlayerfl': INT,
         'fllayerspace': FLOAT,
         'plane': STRING,

         # box params
         'boxvol': FLOAT,
         'lboxx': FLOAT,
         'lboxy': FLOAT,
         'lboxz': FLOAT,

         # MC params
         'mctype': STRING,
         'ncycle': INT,
         'nsamp': INT,
         'maxdisp': FLOAT,
         'maxvol': FLOAT,
         'sameseed': BOOL,

         # parameters for saving
         'nsave': INT,
         'writexyz': STRING,

         # order params
         'orderparam' : STRING,
         'opsamp' : INT,
         'stillsep': FLOAT,
         'q6link': FLOAT,
         'q6numlinks': INT,
         'usenearest': BOOL,

         # FFS params
         'useffs': BOOL,
         'ffsname': STRING,
         'ffsrestart': INT,
         'lambdaA': INT,
         'numint': INT,
         'lambdas': INTLIST,
         'totalqhits': INT,
         'nshots': INT,
         'nbatch': INT,
         'minsuccess': INT,
         'lambdasamp': INT,
         'pruning': BOOL,
         'prunprob': FLOAT,

         # overrides (useful when be have surface particles)
         'o_zperiodic': BOOL,
         'o_boxvol': FLOAT,
         'o_nparsurf': INT,

         # extra parameters used for MD simulations
         'dt': FLOAT,
         'mass': FLOAT,
         'vscale': BOOL,

         # umbrella paramaters
         'nunbiased': INT,
         'numbrellacycles': INT,
         'umb_centre': FLOATLIST,
         'k': FLOATLIST,
         'umbequilcycles': INT,

         # window parameters
         'numwindows': INTLIST,
         'windowsep': FLOATLIST,
         'firstwindow': FLOATLIST,

         # initialisation with seed
         'seed': BOOL,
         'nparseed': INT,
         'seeddensity': FLOAT,
         'seedform': STRING,
         'seedgencorrection': FLOAT,
         }

# default values.  These are used if the
# parameter is not specified in the input file.
DEFAULTS = {
    'k': '0.1',
    'mctype': 'nvt',
    'sameseed': 'no',
    'usenearest': 'yes',
    'surface' : 'no',
    'nsamp' : '1000',
    'nsave' : '1000',

    # umbrella sampling
    'firstwindow': '0.0',
    'numbrellacycles': '1000',
    'numwindows': '10',
    'nunbiased': '10',
    'windowsep': '100',

    # initialisation with seed
    'seed': 'no',
    'seeddensity': '1.0',
    'seedform': 'sc',
    'seedgencorrection': '1.0',
    'umb_centre': '0.0',
    'umbequilcycles': '0',
    'nparseed': '0',

    # legacy surface parameters
    'r6mult': '1.0',
    'r12mult': '1.0'
    }

def _strtointlist(s):
    """
    Converts string e.g. '0,2,3,4,6' to a Python list of integers.
    """

    try:
        ilist = [int(i) for i in s.split(',')]
    except:
        raise ValueError, 'could not convert "{0}" to intlist'.\
              format(s)
    
    return ilist


def _strtofloatlist(s):
    """
    Converts string e.g. '0.1,2.5,3.98,4.1231,6.1' to a Python list of floats.
    """

    try:
        flist = [float(f) for f in s.split(',')]
    except:
        raise ValueError, 'could not convert "{0}" to floatlist'.\
              format(s)
    
    return flist

def _strtobool(s):
    """
    Converts string to bool, note that we want to allow 'yes' and 'no'
    only, and throw an exception otherwise.
    """
    
    if s == 'yes':
        return True
    elif s == 'no':
        return False
    else:
        raise ValueError, 'could not convert "{0}" to boolean'.\
              format(s)

# functions for converting from string to another type.  Note that
# 'int', 'float', 'str' and 'bool' are built-in Python functions.

FUNCS = {INT: int, FLOAT: float, STRING: str, BOOL: _strtobool,
         INTLIST: _strtointlist, FLOATLIST: _strtofloatlist}
