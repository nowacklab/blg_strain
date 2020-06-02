import numpy as np

from .hamiltonian import H_dkx, H_dky
from .utils.const import q, hbar, muB

def berry_mu(E, Psi, xi=1, einsum=True):
    '''
    Calculates the Berry curvature and magnetic moment given the energy
    eigenvalues and eigenvectors for N(=4) bands.

    Params:
    - E: N(=4) x Nkx x Nky array of energy eigenvalues
    - Psi: N(=4) x N(=4) x Nkx x Nky array of energy eigenvectors.
      The first dimension indexes the band, and the second dimension indexes
      components of the eigenvectors.
    - xi: valley index (+1 for K, -1 for K')
    - einsum: if True, use `np.einsum` to multiply (faster than `np.tensordot`)

    Returns:
    - Omega: n(=4) x Nkx x Nky array of Berry curvature (units m^2)
    - Mu: n(=4) x Nkx x Nky array of magnetic moment (units Bohr magneton)
    '''
    hdkx, hdky = H_dkx(xi), H_dky()  # 4x4 matrices

    Omega = np.zeros_like(Psi, dtype='float')  # 4 x 4 x Nkx x Nky; first dim
    Mu = np.zeros_like(Psi, dtype='float')     # summed over bands m != n

    for n, (e_n, psi_n) in enumerate(zip(E, Psi)):
        for m, (e_m, psi_m) in enumerate(zip(E, Psi)):
            if n == m: # sum runs over m != n
                continue

            if einsum:
                # Calculate matrix products using einstein notation
                # These are inner products <n|H'|m> (H' derivative of Hamiltonian)
                # i and l index the components of the eigenvectors for bands n and m
                # the H' matrix is indexed with il to contract these indices
                # j and k index over the kx, ky points and are the dimensions left
                prod1 = np.einsum('ijk,il,ljk->jk', psi_n.conj(), hdkx, psi_m,
                                optimize=True)
                prod2 = np.einsum('ijk,il,ljk->jk', psi_m.conj(), hdky, psi_n,
                                optimize=True)

            else:
                # Equivalent method (slower!)
                # We want C = A * H * B, or c_jk = A_ijk * H_il * B_ljk
                # First sum over l using tensordot
                # Dot product over LAST axis of H and FIRST axis of B
                D1 = np.tensordot(hdkx, psi_m, axes=([-1], [0]))
                D2 = np.tensordot(hdky, psi_n, axes=([-1], [0]))
                # Now we have C = A * D, or c_jk = A_ijk * D_ijk
                # We want to sum over i only, so multiply then sum over axis 0
                prod1 = np.sum(np.multiply(psi_n.conj(), D1), axis=0)
                prod2 = np.sum(np.multiply(psi_m.conj(), D2), axis=0)

            Omega[m, n] = np.imag(np.multiply(prod1, prod2) / (e_n - e_m) ** 2)
            Mu[m, n] = np.imag(np.multiply(prod1, prod2) / (e_n - e_m))

    Omega = Omega.sum(axis=0)  # perform the sum over bands
    Mu = Mu.sum(axis=0)

    Omega = -2 * Omega
    Mu = -q / hbar * Mu / muB  # -> Bohr magnetons
                # [C / (eV * s)] * [(eV * m)^2 / eV] * [1 / A*m^2]
                # result should be dimensionless

    return Omega, Mu
