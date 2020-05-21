# Calculation of microscopic quantities from the bands

import numpy as np
from .utils.const import kB, hbar, m_e

def meff_func(kx, ky, E):
    '''
    Calculates effective mass tensor from the curvature of the bands.
    Specifically, this returns the inverse of the reciprocal effective mass
    tensor, with components (1/m)_{ij} = 1/hbar^2  (d^2E)/(dk_i dk_j)

    The tensor is in units of the electron mass m_e.

    Parameters:
    - kx, ky: Nkx, Nky arrays of kx, ky points
    - E: N(=4) x Nky x Nkx array of energy eigenvalues

    Returns:
    - meff: N(=4) x Nky x Nkx x 2 x 2 array.
        The 1st dimension indexes the energy bands
        The 2nd/3rd dimensions index over ky and kx
        The 4th/5th dimensions are the 2x2 effective mass tensor
    '''
    E_dky, E_dkx = np.gradient(E, ky, kx, axis=(1,2), edge_order=2) # axis1 = y
                                                                    # axis2 = x

    E_dkx_dky, E_dkx_dkx = np.gradient(E_dkx, ky, kx, axis=(1,2), edge_order=2)
    E_dky_dky, E_dky_dkx = np.gradient(E_dky, ky, kx, axis=(1,2), edge_order=2)

    if E.shape[0] != 4:
        raise Exception('Something is wrong... size of E is not 4 x ...')

    oneoverm = np.zeros((E.shape[0], len(ky), len(kx), 2, 2))

    oneoverm[:, :, :, 0, 0] = E_dkx_dkx / hbar**2
    oneoverm[:, :, :, 0, 1] = E_dky_dkx / hbar**2
    oneoverm[:, :, :, 1, 0] = E_dkx_dky / hbar**2
    oneoverm[:, :, :, 1, 1] = E_dky_dky / hbar**2

    # np.linalg.inv will operate over last two axes
    return np.linalg.inv(oneoverm) / m_e  # m_e definition takes care of eV -> J

def feq_func(E, EF, T=0):
    '''
    Fermi-Dirac distribution for calculating electron or hole occupation

    Arguments:
    - E: Energy (eV) - an array with arbitrary dimensions
    - EF: Fermi energy (eV)
    - T: Temperature (K)
    '''

    if T < 1e-10:
        T = 1e-10 # small but finite to avoid dividing by zero
    f = 1 / (1 + np.exp((E - EF) / (kB * T)))
    f[E<0] = 1 - f[E < 0] # for holes

    return f

def check_f_boundaries(f, thresh=0.01):
    '''
    Given an N(=4) x Nky x Nkx array of values for
    the Fermi-Dirac distribution, checks if the values are above a threshold
    along the boundaries of the k space spanned by kx and ky.
    Prints a warning if this condition is not met.
    '''
    assert f.ndim == 3 # n x Nkx x Nky

    for n in range(f.shape[0]): # loop over bands
        below_threshold = True # threshold to check if FD is small enough at boundaries of k-space
        for i in [0, -1]:
            if (f[n, i, :] > thresh).any():
                below_threshold = False
            elif (f[n, :, i] > thresh).any():
                below_threshold = False
        if not below_threshold:
            print('F-D dist in band %i not smaller than %f at boundaries!' %(n, thresh))