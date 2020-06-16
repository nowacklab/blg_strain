import numpy as np

from .berry import berry_mu
from .hamiltonian import Hfunc

def get_bands(kxlims=[-0.35e9, .35e9], kylims=[-0.35e9, .35e9], Nkx=200,
                Nky=200, xi=1, Delta=0, delta=0, theta=0, twobytwo=False,
                eigh=False):
    '''
    Calculate energy eigenvalues, eigenvectors, berry curvature, and magnetic
    moment for a rectangular window of k-space.

    Parameters:
    - kxlims, kylims: length-2 arrays of min and max wave vectors (nm^-1)
    - Nkx, Nky: number of k points in each dimension
    - xi: valley index (+1 for K, -1 for K')
    - Delta: interlayer asymmetry (eV)
    - delta: uniaxial strain
    - theta: angle of uniaxial strain to zigzag axis
    - twobytwo: if True, use 2x2 Hamiltonian (N=2 for all returned values)
    - eigh: if True, use np.linalg.eigh; if False use np.linalg.eig

    Returns:
    - kx, ky: Nkx, Nky arrays of kx, ky points
    - Kx, Ky: Nkx x Nky meshgrid of kx, ky points (note: we use `ij` indexing
        compatible with scipy spline interpolation methods)
    - E: N(=4) x Nkx x Nky array of energy eigenvalues
    - Psi: N(=4) x N(=4) x Nkx x Nky array of eigenvectors
    '''
    kx = np.linspace(kxlims[0], kxlims[1], Nkx)
    ky = np.linspace(kylims[0], kylims[1], Nky)

    Kx, Ky = np.meshgrid(kx, ky, indexing='ij')


    E, Psi = _get_bands(Kx, Ky, xi=xi, Delta=Delta, delta=delta,
                        theta=theta, twobytwo=twobytwo, eigh=eigh)

    return kx, ky, Kx, Ky, E, Psi


def _get_bands(Kx, Ky, xi=1, eigh=True, **params):
    '''
    Calculate energy eigenvalues, eigenvectors, berry curvature, and magnetic
    moment for a rectangular window of k-space.

    Parameters:
    - Kx, Ky: Nkx x Nky meshgrid of kx, ky points (using 'ij' indexing)
    - xi: valley index (+1 for K, -1 for K')
    - eigh: if True, use np.linalg.eigh; if False use np.linalg.eig
    - params: passed to `hamiltonian.H_func`

    Returns:
    - E: N(=4) x Nkx x Nky array of energy eigenvalues
    - Psi: N(=4) x N(=4) x Nkx x Nky array of eigenvectors
    '''
    H = Hfunc(Kx, Ky, xi=xi, **params)

    H = H.transpose(2,3,0,1) # put the 4x4 in the last 2 dims for eigh

    # check if Hermitian
    if not (H == H.transpose(0,1,3,2).conjugate()).all():
        raise Exception('Hamiltonian is not Hermitian! Cannot use eigh.')

    if eigh:
        E, Psi = np.linalg.eigh(H)  # using eigh for Hermitian
                                # eigenvalues are real and sorted (low to high)
    else:
        E, Psi = np.linalg.eig(H)  # Option to use eig instead of eigh

    # Shapes - E: Nkx x Nky x 4, Psi: Nkx x Nky x 4 x 4
    E = E.transpose(2,0,1) # put the kx,ky points in last 2 dims
    Psi = Psi.transpose(2,3,0,1) # put the kx,ky points in last 2 dims
    # now E[:, 0, 0] is a length-4 array of eigenvalues
    # and Psi[:, :, 0, 0] is a 4x4 array of eigenvectors (in the columns)

    if eigh:
        Psi = fix_first_component_sign(Psi)

    else:
        E, Psi = sort_eigen(E, Psi)
        E = E.real




    # Finally, transpose first 2 dimensions to put the eigenvectors in the rows
    Psi = Psi.transpose((1,0,2,3))

    # Now E[n, 0, 0] and Psi[n, :, 0, 0] give the energy and eigenstates

    return E, Psi


def sort_eigen(eigs, vecs):
    '''
    Sort eigenvalues and the corresponding eigenvectors in order of increasing
    eigenvalues.

    Params:
    - eigs: N x ... array of eigenvalues
    - vecs: N x N x ... array of eigenvectors (in the columns)

    Returns:
    - eigs, vecs: sorted arrays in order of increasing eigenvalues
    '''
    indE = np.indices(eigs.shape)  # Get the indices such that
                                   # eigs[tuple(indE)] == eigs
    indV = np.indices(vecs.shape)

    indE[0] = eigs.argsort(axis=0)  # Sort the indices along the first axis
    indV[1] = indE[0]  # vectors sorted along *second* axis

    return eigs[tuple(indE)], vecs[tuple(indV)]


def fix_first_component_sign(Psi):
    '''
    Addresses sign ambiguity in eigenvectors by focing first component positive
    '''
    # Create a multiplier: 1 if the first component is positive
    #                     -1 if the first component is negative
    multiplier = 2 * (Psi[0].real > 0) - 1  # shape 4 x Nkx x Nky
    Psi *= multiplier  # flips sign of eigenvectors where 1st component is -ive
                       # NOTE: broadcasting rules dictate that the multiplier is
                       # applied to all components of the first dimension, thus
                       # flipping the sign of the entire vector

    if (Psi[0].real < 0).any():  # double check that all positive
        raise Exception('Fixing sign ambiguity failed! There are eigenvectors \
                with a negative first component!')

    return Psi
