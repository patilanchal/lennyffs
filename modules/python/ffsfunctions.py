# ffsfunctions.py
# James Mithen
# j.mithen@surrey.ac.uk

"""
FFS specific functions.

FUNCTIONS:
getshotdict       - return shot dictionary at a given interface.
getpickparams     - return dictionary of parameters from pickle file.
getnumsuccess     - return number of successful shots at a given
                    interface.
takeshot          - take FFS shot from a given configuration.
savelambda0config - save the particle positions and time of hitting
                    first FFS interface (lambda0).
"""

import glob
import os
import pickle
import sys

import numpy as np

import funcselector
import readwrite

def getshotdict(nint):
    """Return shot dictionary from pickle file at interface nint."""
    
    pfile = open('interface{0}.pkl'.format(nint), 'rb')
    shotdict = pickle.load(pfile)
    pfile.close()
    return shotdict


def getpickparams():
    """Return params dictionary from pickle file."""
    
    pfile = open('params.pkl', 'rb')
    params = pickle.load(pfile)
    pfile.close()
    return params


def getboxdims(infile):
    """
    Return box dimensions from XYZ file if present.  If not present,
    return None.
    """

    # box dimension will be given on 2nd line of file as e.g.  
    # '# boxdims 91.3213283335 91.3213283335 91.3213283335'
    lines = open(infile, 'r').readlines()
    dimline = lines[1]

    # strip will get rid of the \n character
    if dimline.strip():
        spl = dimline.split()
        lx, ly, lz = float(spl[-3]), float(spl[-2]), float(spl[-1])
        return lx, ly, lz
    return None

def getnumsuccess(nint):
    """Return number of succesful shots at interface nint. """
    
    files = glob.glob("pos{0}_*.xyz".format(nint))
    nsuccess = len(files)
    return nsuccess

def takeshot(initfile, nint, params):
    """Take FFS shot from configuration in initfile."""

    # lambda A is the order parameter below which the system is in the
    # 'initial phase'.
    lamA = params['lambdaA']

    # order parameter at the interface we are going to; when the
    # system hits either lamint or lamA, the shot is over (having been
    # a success or failure respectively).
    lamint = params['lambdas'][nint+1]
    
    # read positions from file
    params['restartfile'] = initfile
    positions = readwrite.rxyz(params['restartfile'])
    
    # get correct functions for total energy and mccycle
    fsel = funcselector.FuncSelector(params)
    totalenergyfunc = fsel.TotalEnergyFunc()
    mccyclefunc = fsel.MCCycleFunc()
    opfunc = fsel.SingleOrderParamFunc()
    
    # get initial potential energy and order parameter
    epot = totalenergyfunc(positions,params)
    oparam = opfunc(positions,params)
    print "Initial OP: {0}".format(oparam)
    
    # num cycles before computing bopx
    lamsamp = params['lambdasamp']
    params['cycle'] = lamsamp
    
    # these variables are only relevant when pruning is used
    weight = 1
    lowint = nint - 1 # next interface to drop below
    lowlambda = params['lambdas'][lowint]
    ttot = 0
    pruned = False
    
    while (oparam >= lamA) and (oparam < lamint):

        # pruning->test if we have gone through an interface below
        if params['pruning']:
            
            # check if we have hit the next interface in turn: note
            # while loop since we may have gone though more than a
            # single interface since last check of order param.
            while (oparam <= lowlambda):
                
                # we can only prune if the lower interface is at least
                # lambda0
                if (lowint >= 0):

                    # kill with prob prunprob
                    r = np.random.rand()
                    if (r < params['prunprob']):
                        print 'Run killed by prune since OP <= {0}'\
                              .format(lowlambda)
                        pruned = True
                        # leave pruning while loop
                        break
                    else:
                        print 'Run not killed by prune with OP <= {0}'\
                              .format(lowlambda)
                        
                        # run continued with increased weight
                        weight = weight * 1.0/(1.0 - params['prunprob'])
                        # get next interface for pruning
                        lowint = lowint - 1
                        lowlambda = params['lambdas'][lowint]
                        
                else:
                    # we have either already tried to prune at lambda0
                    # and not killed the run, or we started from lambda0
                    # we need to break out of while loop and wait for run
                    # to either succeed or return to lambdaA (phase A)
                    break

        # we were killed by pruning, exit while loop
        if pruned:
            break
                
        # make some trial moves
        positions, epot = mccyclefunc(positions, params, epot)
        ttot = ttot + lamsamp

        # evaluate OP
        oparam = opfunc(positions, params)
        print "OP: {0}".format(oparam)

    # if oparam >= lamint, we have hit the next interface, otherwise
    # we have failed (returned to original phase).
    if (oparam >= lamint):
        success = True
    else:
        success = False

    return success, weight, ttot, positions

def savelambda0config(qhits, thit, oparam, positions, params, wfunc):
    """Save configuration at lambda0 and add to the times file."""
    
    fnametime = 'times.out'
    fnamepos = 'pos0_{0}.xyz'.format(qhits)

    # create file times.out if hit lambda0 for the first time
    if qhits == 1: 
        fout = open(fnametime,'w')
        fout.write('#Time OP\n')
    else:
        fout = open(fnametime, 'a')

    # write to file
    fout.write('{0} {1}\n'.format(thit, oparam))
    fout.close()

    # write out positions at the interface lambda_0
    wfunc(fnamepos, positions, params)        
    return
