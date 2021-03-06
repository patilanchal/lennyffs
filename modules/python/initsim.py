# initsim.py
# James Mithen
# j.mithen@surrey.ac.uk

"""
Functions for initializing simulation by reading params from 'in',
making box, initialising positions etc.  This module uses the Atomic
Simulation Environment (ASE) package in order to initialize positions
on a lattice.  The code needed from ASE is included in
modules/python/ase. The entire codebase and documentation for ASE is
available at https://wiki.fysik.dtu.dk/ase/.

FUNCTIONS:
readparams                  - read parameters from 'in' and return as
                              dictionary.
getparams                   - read params, make them numerical, add any
                              missing.
checkparams                 - a few sanity checks on the parameters we read.
addparams                   - add useful parameters to params dictionary.
addparamssurf               - add parameters to params dictionary if have
                              surface.
addparamsnosurf             - add parameters to params dictionary if no
                              surface.
initpositionsvelocities     - wrapper for initialising particle positions
                              and velocities for MD.
initpositions               - wrapper for initialising particle positions.
initpositionsnosurf         - init particle positions if no surface.
initlatticepositions        - init particle positions on a lattice.
initflpositionsrandom       - init fluid positions randomly above surface.
initflpositionslayer        - init fluid positions in layers above surface.
initseedpositions           - init seed particle positions for umbrella
                              sampling
initpositionsseed           - init positions of fluid around seed using
                              a defined excluded region
initpositionssurf           - init particle positions if have surface.
initvelocitiesgauss         - init velocites from Maxwell-Boltzmann
                              distribution at desired temperature
initvelocities              - init particle velocities (for MD simulation).
maketriples                 - a generator for seed particle co-ordinates
                              for umbrella-sampling
"""

import sys
import os
import numpy as np
import mcfuncs
import readwrite
import params
import writeoutput
import ase.lattice.surface as ase
from ffsfunctions import getboxdims

def readparams():
    """Read simulation parameters from 'in' file."""
    
    pdict = {} # dictionary containing params
    fname = os.getcwd() + '/in'
    f = open(fname,'r')
    flines = f.readlines()
    rerror = False
    
    for line in flines:
        # skip comments (rudimentary method)
        if '#' in line:
            continue
        line = line.split()
        if line:
            # note that this interface should handle conversion from
            # string to e.g. int correctly
            p = params.Param(line[0], line[1])
            if p.value is None:
                # something went wrong, we should have had an error
                # msg on stdout
                rerror = True
            else:
                pdict[p.name] = p.value
    if rerror:
        return {}
    return pdict

def getparams():
    """
    Read simulation parameters from in file and compute other useful
    parameters from these.  Returns a dictionary containing names and
    values of these parameters.
    """
    
    # read parameters from 'in' file
    pdict = readparams()
    if not pdict:
        # something went wrong reading params file
        sys.exit("Error: I couldn't read the 'in' file properly")

    # add in any default values
    defaults = params.get_defaults()

    # overwrite any values in defaults that currently exist
    defaults.update(pdict)
    pdict = defaults
        
    # check that the input actually makes sense, can we actually do a
    # simulation with this info?
    pdict = checkparams(pdict)

    # add some parameters to the dictionary that are useful
    pdict = addparams(pdict)
    return pdict

def checkparams(pdict):
    """Some sanity checks on the parameters in the input file."""

    # only one simple check at the moment, this should be added to
    if 'useffs' in pdict and pdict['useffs']:
        if (len(pdict['lambdas']) != pdict['numint'] + 1):
            sys.exit('Error: num interfaces and lambdas given do not match up')

    return pdict

def addparams(pdict):
    """Add some useful parameters to the dictionary."""
        
    # eps/k_bT
    pdict['epsovert'] = 1.0 / pdict['Tstar']
    # 4eps/k_bT
    pdict['eps4'] = 4.0 / pdict['Tstar'] 
    # cutoff radius
    rc2 = pdict['rcut']**2
    pdict['rcsq'] = rc2
    
    # potentials at cutoff
    if pdict['potential'] == 'ipl':
        vrc = 1.0 / pdict['rcut']**pdict['potexponent']
        vrc2 = vrc
    elif pdict['potential'] == 'len':
        rc2i = 1.0/rc2
        rc6i = rc2i**3
        rc12i = rc6i**2
        # particle-particle
        vrc = rc12i - rc6i
        # particle-surface
        
        if not pdict['surface']:
            # r6mult and r12 mult are redundant, set to 1
            pdict['r6mult'] = pdict['r12mult'] = 1.0
            
        vrc2 = pdict['r12mult']*rc12i - pdict['r6mult']*rc6i
    elif pdict['potential'] == 'gauss':
        vrc = np.exp(-rc2)
        vrc2 = vrc

    # for len, this is in units of 4eps, for gauss and IPL in units of eps
    pdict['vrc'] = vrc 
    pdict['vrc2'] = vrc2

    # add parameters specific to whether there is a surface
    if pdict['surface']:
        pdict = addparamssurf(pdict)
    else:
        pdict = addparamsnosurf(pdict)
        
    return pdict

def addparamssurf(pdict):
    """Add parameters to dictionary for surface."""
    
    # since we have a surface, we are not periodic in z
    pdict['zperiodic'] = False

    # make surface close packed if not given in in file
    if 'plane' not in pdict:
        if pdict['surftype'] == 'fcc':
            pdict['plane'] = '111'
        elif pdict['surftype'] == 'hcp':
            pdict['plane'] = '0001'
    
    # compute number of particles in surface
    nparlayer = pdict['lysurf']*pdict['lxsurf']
    nparsurf = nparlayer * pdict['nlayersurf']
    pdict['nparlayer'] = nparlayer
    pdict['nparsurf'] = nparsurf

    # get lattice parameters and set dimensions of simulation
    # box in x and y
    if pdict['surftype'] == 'fcc':
        
        # alat is for the conventional (cubic) unit cell
        alat = 2.0**(2.0/3.0)/pdict['nlatt']**(1.0/3.0)
        pdict['alat'] = alat
        if pdict['plane'] == '111':
            pdict['lboxx'] = (alat/2.0**0.5)*pdict['lxsurf']
            pdict['lboxy'] = (alat/2.0**0.5)*np.sin(np.pi/3.0)*pdict['lysurf']
            pdict['dzsurf'] = alat/3.0**0.5
        elif pdict['plane'] == '100':
            pdict['lboxx'] = (alat/2.0**0.5)*pdict['lxsurf']
            pdict['lboxy'] = (alat/2.0**0.5)*pdict['lysurf']
            pdict['dzsurf'] = alat/2.0
        elif pdict['plane'] == '110':
            pdict['lboxx'] = alat*pdict['lxsurf']
            pdict['lboxy'] = (alat/2.0**0.5)*pdict['lysurf']
            pdict['dzsurf'] = alat/2.0**(3.0/2.0)
            
    elif pdict['surftype'] == 'bcc':
        # alat is the conventional (cubic) unit cell
        alat = 2.0**(1.0/3.0)/ pdict['nlatt']**(1.0/3.0)
        pdict['alat'] = alat
        if pdict['plane'] == '100':
            pdict['lboxx'] = alat*pdict['lxsurf']
            pdict['lboxy'] = alat*pdict['lysurf']
            pdict['dzsurf'] = alat/2.0
            
    elif pdict['surftype'] == 'hcp':
        # conventional (hexagonal) unit cell
        alat = 2.0**(1.0/6.0)/pdict['nlatt']**(1.0/3.0)
        clat = alat*(8.0/3.0)**0.5 # perfect hcp parameter
        pdict['alat'] = alat
        pdict['clat'] = clat
        if pdict['plane'] == '0001':
            pdict['lboxx'] = alat*pdict['lxsurf']
            pdict['lboxy'] = alat*pdict['lysurf']*np.sin(np.pi/3.0)
            pdict['dzsurf'] = clat/2.0
        elif pdict['plane'] == '1010':
            # note this is actually 10\bar{1}0 or (1,0,-1,0) plane
            pdict['lboxx'] = alat*pdict['lxsurf']
            pdict['lboxy'] = (clat/2.0)*pdict['lysurf']
            pdict['dzsurf'] = alat*(3.0**0.5/2.0)

    # get number of fluid particles
    if pdict['flinit'] == 'random':
        # init fluid particles to random positions, using nparfl for
        # number
        pdict['nparfl'] = int(pdict['nparfl'])
        pdict['rcinit'] = float(pdict['rcinit'])
        
    elif pdict['flinit'] == 'layer':
        # initialise fluid particles in layers, using nlayerfl for
        # number nb we change lboxz in this case from what is given in
        # boxvol in 'in' and we make fllayerspace the spacing between
        # initial fluid layers
        nparfl = nparlayer * pdict['nlayerfl']
        pdict['nparfl'] = nparfl
        pdict['npartot'] = nparsurf + nparfl
        lboxz = pdict['boxvol']/(pdict['lboxx']*pdict['lboxy'])
        pdict['lboxz'] = lboxz
        # z space 'occupied' by surface
        zsurf = (pdict['nlayersurf'] - 1)*pdict['dzsurf']
        # z space not 'occupied' by surface
        zfluid = lboxz - zsurf
        pdict['fllayerspace'] = (zfluid /
                                 (pdict['nlayerfl'] + 1))/pdict['dzsurf']

    # total number of particles
    pdict['npartot'] = pdict['nparsurf'] + pdict['nparfl']

    # overrides: The following overrides mean we can specify
    # non-standard simulation setups in the case where there is a
    # surface.
    #
    # i) Allow lboxx, lboxy and lboxz to be overridden by o_boxvol.
    #    This is useful for simulations with seed particles.
    if 'o_boxvol' in pdict:
        lb = pdict['o_boxvol']**(1.0/3.0)
        pdict['lboxx'] = lb
        pdict['lboxy'] = lb
        pdict['lboxz'] = lb
    # ii) Allow 'zperiodic' to be overridden.
    if 'o_zperiodic' in pdict:
        pdict['zperiodic'] = pdict['o_zperiodic']
    # iii) Allow nparsurf to be overridden.
    if 'o_nparsurf' in pdict:
        pdict['nparsurf'] = pdict['o_nparsurf']
        pdict['npartot'] = pdict['nparsurf'] + pdict['nparfl']
    
    return pdict

def addparamsnosurf(pdict):
    """Add parameters to dictionary for no surface."""
    
    # obviously zero particles in surface
    pdict['nparsurf'] = 0
    
    # since we have no surface, we are periodic in z
    pdict['zperiodic'] = True
    
    nparfl = pdict['nparfl']
    pdict['npartot'] = nparfl

    # get box dimensions
    # for both npt and nvt simulations, the dims are set as follows
    # - If lboxx, lboxy and lboxz are in pdict, use these
    # - Otherwise, if boxvol is given in pdict, we will have a cubic
    #   box of dimension boxvol**(1/3)
    # - If neither [lboxx,lboxy,lboxz] nor boxvol is in pdict
    #   we use nstar to set the box dimensions
    # - If none of the above has set the box dimensions, we have a
    #   problem (!)
    # Finally, we try getting the box dims from the xyz file.  Note
    # this will override the above!
    if ('lboxx' in pdict) and ('lboxy' in pdict) and ('lboxz' in pdict):
        pass
    else:
        if 'boxvol' in pdict:
            lbox = pdict['boxvol']**(1.0/3.0)
            pdict['lboxx'] = lbox
            pdict['lboxy'] = lbox
            pdict['lboxz'] = lbox        
        elif 'nstar' in pdict:
            # use nstar to set box size (beware of coexistence region)
            nstar = pdict['nstar']
            lbox = (nparfl/nstar)**(1.0/3.0)
            pdict['lboxx'] = lbox
            pdict['lboxy'] = lbox
            pdict['lboxz'] = lbox
        else:
            # we haven't set the box size (!)
            print "Warning, box size has not been set properly!"

    # if restarting then try over-riding with box volume from the XYZ file
    if (pdict['simulation'] == 'restart'):
        boxdims = getboxdims(pdict['restartfile'])
        if boxdims:
            pdict['lboxx'] = boxdims[0]
            pdict['lboxy'] = boxdims[1]
            pdict['lboxz'] = boxdims[2]
            
    return pdict

def initpositionsvelocities(params):
    """
    Initialize both positions and velocities for MD simulation.
    """

    if params['simulation'] == 'restart':
        # we can restart either from a .pkl file (in which case we
        # expect both positions and velocities) or from a .xyz file
        # (in which case we expect only positions).  In the latter
        # case, we initialize the velocities randomly with
        # Maxwell-Boltzmann distribution.
        if params['restartfile'].endswith('.pkl'):
            # the restart file should be a pickle file that contains
            # both the positions and the velocities.
            return writeoutput.readmdpick(params['restartfile'])
        else:
            return readwrite.rxyz(params['restartfile']),\
                   initvelocitiesgauss(params)            
    else:
        # note unlike in the case of restarting a simulation, we
        # initialize the velocities randomly.
        return initpositions(params), initvelocities(params)

def initpositions(params):
    """
    Initialize positions.  The length of the box in the x and y
    directions are determined from the number of surface particles in
    each direction (lxsurf and lysurf) and the lattice parameter of
    the surface.  The fluid particles are placed above the surface.
    The spacing between planes of fluid particles is determined by
    ensuring that N/V_box = n*, where N is the number of fluid
    particles and V_box is the box volume EXCLUDING the volume of the
    surface.
    """

    if params['simulation'] == 'restart':
        return readwrite.rxyz(params['restartfile'])
    else:
        if params['surface']:
            return initpositionssurf(params)
        elif params['seed']:
            return initpositionsseed(params)
        else:
            return initpositionsnosurf(params)

def initpositionsnosurf(params):
    """Initialize positions of fluid particles with no surface."""
    
    nparfl = params['nparfl']
    lboxx = params['lboxx']
    lboxy = params['lboxy']
    lboxz = params['lboxz']
    rcinit = params['rcinit']
    sameseed = params['sameseed']    
    rcinitsq = rcinit**2.0
    pos = np.empty([nparfl,3])

    # excluded region: no fluid particles will be placed in this
    # region.  We default to False so that fluid particles are placed
    # throughout the whole box.
    exregion = params.get('exregion', False)
    exxmin = params.get('exxmin', 0.0)
    exxmax = params.get('exxmax', 0.0)
    exymin = params.get('exymin', 0.0)
    exymax = params.get('exymax', 0.0)
    exzmin = params.get('exzmin', 0.0)
    exzmax = params.get('exzmax', 0.0)    

    pos[:,0], pos[:,1], pos[:,2] = mcfuncs.\
                                   initpositionsnosurff(nparfl, lboxx,
                                                        lboxy, lboxz,
                                                        rcinitsq,
                                                        # excluded region
                                                        exregion,
                                                        exxmin, exxmax,
                                                        exymin, exymax,
                                                        exzmin, exzmax,
                                                        sameseed)

    return pos

def initlatticepositions(params,nlayers):
    """
    Return nlayers of positions according to lattice type/plane and
    shift positions so that no atoms are on the edges of the box.
    """

    lxsurf = params['lxsurf']
    lysurf = params['lysurf']
    alat = params['alat']

    if params['surftype'] == 'fcc':

        if params['plane'] == '111':
            surf = ase.fcc111('O', a=alat, size=(lxsurf,lysurf,nlayers),
                              orthogonal=True)
            positions = surf.positions
            positions[:,0] = positions[:,0] + (alat/2.0**0.5)/4.0
            positions[:,1] = (positions[:,1] +
                              (1.0/2.0)*(3.0**0.5)*(alat/2.0**0.5)/4.0)

        elif params['plane'] == '100':
            surf = ase.fcc100('O',a=alat,size=(lxsurf,lysurf,nlayers))
            positions = surf.positions
            positions[:,0] = positions[:,0] + (alat/2.0**0.5)/4.0
            positions[:,1] = positions[:,1] + (alat/2.0**0.5)/4.0

        elif params['plane'] == '110':
            surf = ase.fcc110('O',a=alat,size=(lxsurf,lysurf,nlayers))
            positions = surf.positions
            positions[:,0] = positions[:,0] + alat/4.0
            positions[:,1] = positions[:,1] + (alat/2.0**0.5)/4.0

    elif params['surftype'] == 'bcc':

        if params['plane'] == '100':
            surf = ase.bcc100('O', a=alat, size=(lxsurf,lysurf,nlayers))
            positions = surf.positions
            positions[:,0] = positions[:,0] + alat/2.0
            positions[:,1] = positions[:,1] + alat/2.0

    elif params['surftype'] == 'hcp':

        clat = params['clat']
        if params['plane'] == '0001':
            surf = ase.hcp0001('O', a=alat, c=clat, size=(lxsurf,lysurf,nlayers),
                               orthogonal=True)
            positions = surf.positions
            positions[:,0] = positions[:,0] + alat/4.0
            positions[:,1] = positions[:,1] + (1.0/2.0)*(3.0**0.5)*alat/4.0

        elif params['plane'] == '1010':
            surf = ase.hcp10m10('O', a=alat, c=clat, size=(lxsurf,lysurf,nlayers))
            positions = surf.positions
            positions[:,0] = positions[:,0] + alat/4.0
            positions[:,1] = positions[:,1] + clat/4.0
    
    return positions

def initflpositionsrandom(params):
    """Initialise fluid positions randomly above surface."""
    
    nparfl = params['nparfl']
    lboxx = params['lboxx']
    lboxy = params['lboxy']
    lboxz = params['lboxz']
    rcinit = params['rcinit']
    sameseed = params['sameseed']
    rcinitsq = rcinit**2.0
    pos = np.empty([nparfl,3])

    # make sure we initialise fluid particles above surface
    zspace = params['nlayersurf']*(params['clat']/2.0)
    lboxzfl = params['lboxz'] - zspace

    pos[:,0],pos[:,1],pos[:,2] = mcfuncs.\
                                 initpositionsnosurff(nparfl, lboxx,
                                                      lboxy, lboxzfl,
                                                      rcinitsq,
                                                      # no excluded region
                                                      False,
                                                      0, 0, 0, 0, 0, 0,
                                                      sameseed)
    pos[:,2] = pos[:,2] + zspace

    return pos

def initflpositionslayer(params):
    """Initialise fluid positions in layers commensurate with surface."""
    
    alat = params['alat']
    lxfl = params['lxsurf']
    lyfl = params['lysurf']
    nlayerfl = params['nlayerfl']

    flpositions = initlatticepositions(params,params['nlayerfl'])

    # multiple z positions by layerspacing
    flpositions[:,2] = flpositions[:,2]*params['fllayerspace']

    # raise z positions above surface
    flpositions[:,2] = (flpositions[:,2] +
                        params['dzsurf']*(params['nlayersurf'] - 1) + 
                       (params['fllayerspace']*params['dzsurf']))
    return flpositions

def deduce_seed_size(params):
    """Determine required seed size based on parameters"""
    if params['orderparam'] == 'nld':
        return params['umb_centre'][0]
    if params['orderparam'] == 'ntf':
        return params['umb_centre'][0]
    if params['orderparam'] == 'q6global':
        if params['seedform'] == 'fcc':
            perfectQ6 = 0.57452
        if params['seedform'] == 'bcc':
            perfectQ6 = 0.51069
        if params['seedform'] == 'sc':
            perfectQ6 = 0.35355
        return (params['umb_centre'][0]/perfectQ6)*params['nparfl']
    if params['orderparam'] == 'potenergy':
        return 0.0
    if params['orderparam'] == 'nbccncp':
        return params['umb_centre'][0] + params['umb_centre'][1]
    return 0.0

def initseedpositions(params):
    """Initialize seed particle positions."""

    if params['seedform'] == 'fcc':
        pars_in_cell = 4.0
    elif params['seedform'] == 'bcc':
        pars_in_cell = 2.0
    elif params['seedform'] == 'sc':
        pars_in_cell = 1.0
    else:
        pars_in_cell = 1.0
        
    # alatt is conventional unit cell size
    alatt = (pars_in_cell/params['seeddensity'])**(1.0/3.0)

    # generate seed particle positions from maketriples and scale by alatt
    #print params['nparseed']
    seedpositions = alatt*np.array([c for c in maketriples(int(params['seedgencorrection']*params['nparseed']), params['seedform'])])

    # shift seed cluster to centre of box
    if params['nparseed'] != 0:
        seedpositions = np.array([[params['lboxx']/2,params['lboxy']/2,params['lboxz']/2]])+seedpositions
        
    return seedpositions
    

def initpositionsseed(params):
    """
    Initialize positions with seed present.  Note that the seed is not
    treated as a surface.
    """
    # initialise seed of nparseed particles
    seedpositions = initseedpositions(params)
    
    # set excluded region for fluid particles based on seed positions...
    if params['nparseed'] != 0:
        params['exregion'] = True
        params['exxmin'] = min(seedpositions[:, 0])
        params['exxmax'] = max(seedpositions[:, 0])
        params['exymin'] = min(seedpositions[:, 1])
        params['exymax'] = max(seedpositions[:, 1])
        params['exzmin'] = min(seedpositions[:, 2])
        params['exzmax'] = max(seedpositions[:, 2])
    else:
        params['exregion'] = False
    
    # initialise randomly nparfl - nparseed
    params['nparfl'] = params['nparfl'] - int(params['seedgencorrection']*params['nparseed'])
    flpositions = initpositionsnosurf(params)
    params['nparfl'] = params['nparfl'] + int(params['seedgencorrection']*params['nparseed'])

    # combine the 2 lists if both exist, else return the one that does
    if len(seedpositions) == 0:
        allpositions = flpositions
    elif len(flpositions) == 0:
        allpositions = seedpositions
    else:
        allpositions = np.append(seedpositions, flpositions, axis=0)
    return allpositions
    
def initpositionssurf(params):
    """Initialize positions with surface present."""
    
    # surface positions
    surfpositions = initlatticepositions(params,params['nlayersurf'])    

    # fluid positions
    if params['flinit'] == 'random':
        # init fluid positions randomly, with lboxz as given in 'in' file
        flpositions = initflpositionsrandom(params)
    elif params['flinit'] == 'layer':
        # init fluid positions in layers, with lboxz given by 'layerspace'
        flpositions = initflpositionslayer(params)
    else:
        sys.exit('Error: no fluid particles init specified')

    # array ordered as surface atoms, then fluid atoms
    allpositions = np.append(surfpositions,flpositions, axis=0)

    return allpositions

def initvelocitiesgauss(params):
    """
    Initialize velocities from Maxwell-Boltzmann distribution at the
    desired temperature.
    """
    
    # get parameters required from dictionary
    npar = params['npartot']
    temp = params['Tstar']

    # for each velocity component, we do the following:
    # (i)   init velocity from Gaussian with sigma = sqrt(k_B T / m)
    # (ii)  add/subtract from all velocities so that net mom is zero
    # (iii) multiply by scale factor so that kinetic temp is exact
    # Furthermore, note that we are assuming mass is = 1 here    

    stdev = temp**0.5

    vels = np.empty((npar, 3))

    for i in range(3):
        vels[:,i] = np.random.normal(0.0, stdev, npar)
        sumv = np.sum(vels[:,i]) / npar
        vels[:,i] = vels[:,i] - sumv
        sumv2 = np.sum(vels[:,i]**2) / npar
        fs = (temp / sumv2)**0.5
        vels[:,i] = vels[:,i]*fs

    return vels

def initvelocities(params):
    """
    Initialize velocities.
    
    For now give particles random velocities consistent with
    temperature, and with zero net momentum.
    """

    # get parameters required from dictionary
    npar = params['npartot']
    temp = params['Tstar']

    # random velocities
    vels = np.random.random((npar, 3)) - 0.5
    sumv = np.sum(vels, axis = 0) / npar
    sumv2 = np.sum(vels**2, axis = 0) / npar

    # scale factor
    fs = (temp / sumv2)**0.5

    # numpy automatically handles the different shapes of these arrays
    # correctly (yay!)
    vels = (vels - sumv)*fs

    return vels


def maketriples(Ntot,structure):
    """
    Generates co-ordinates for a roughly-cubic FCC seed
    particle of Ntot particles
    """
    count = 0
    if count == Ntot:
        raise StopIteration
    i,j,k = 3*(0,)
    yield (i,j,k)
    count += 1
    if count == Ntot:
        raise StopIteration
    nmax = 0
    while True:
        nmax += 1
        for n in range(-nmax,nmax+1):
            for m in range(-nmax,nmax+1):
                for l in range(-nmax,nmax+1):
                    if nmax in (n,m,l) or -nmax in (n,m,l):
                        yield (n,m,l)
                        count += 1
                        if count == Ntot:
                            raise StopIteration

                        if structure == 'fcc':

                            yield (n+0.5,m+0.5,l)
                            count += 1
                            if count == Ntot:
                                raise StopIteration

                            yield (n,m+0.5,l+0.5)
                            count += 1
                            if count == Ntot:
                                raise StopIteration

                            yield (n+0.5,m,l+0.5)
                            count += 1
                            if count == Ntot:
                                 raise StopIteration
                             
                        elif structure == 'bcc':

                            yield (n+0.5,m+0.5,l+0.5)
                            count += 1
                            if count == Ntot:
                                raise StopIteration

                        elif structure == 'sc':
                            continue
                            
