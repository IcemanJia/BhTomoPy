# -*- coding: utf-8 -*-
"""
Created on Tue Jun 21 20:55:29 2016

@author: giroux

Copyright 2017 Bernard Giroux, Jerome Simon
email: Bernard.Giroux@ete.inrs.ca

This file is part of BhTomoPy.

BhTomoPy is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import inspect
import dis
import numpy as np
import scipy.signal
import sqlalchemy.types as types
from PyQt5.QtCore import QThread

from sqlalchemy.ext.declarative import declarative_base  # Base creates the objects' mapping (i.e. their association with the tables).
Base = declarative_base()                                # Must be present in the child-most module in order not to cause inter-dependencies

class ComputeThread(QThread): # Class that simplify the threading of a function. Simply create a thread for a giving function
    def __init__(self, function_to_compute):
        QThread.__init__(self)
        self.compute = function_to_compute

    def run(self):
        self.compute()

def Hook(Type, value, traceback):  # PyQt5 overrides Eclipse's exception catching. 'Hook' solves this issue.
    initial_ctx = traceback.tb_next
    while initial_ctx is not None:
        initial_ctx = initial_ctx.tb_next
    sys.__excepthook__(Type, value, traceback)


sys.excepthook = Hook


def nargout():  # TODO FIXME either doesn't work as of 3.6 or doesn't work on windows
    """
    Returns how many values the caller is expecting

    taken from
    http://stackoverflow.com/questions/16488872/python-check-for-the-number-of-output-arguments-a-function-is-called-with
    """
    f = inspect.currentframe()
    f = f.f_back.f_back
    c = f.f_code
    i = f.f_lasti
    bytecode = c.co_code
    instruction = bytecode[i + 3]
    if instruction == dis.opmap['UNPACK_SEQUENCE']:
        howmany = bytecode[i + 4]
        return howmany
    elif instruction == dis.opmap['POP_TOP']:
        return 0
    return 1


def set_tick_arrangement(grid):

    if grid.grx[0] < 0:
        tick_range = grid.grx[0] - grid.grx[-1]
    elif grid >= 0:
        tick_range = grid.grx[-1] - grid.grx[0]

    nticks = 4
    tick_step = np.round(tick_range / nticks)

    if grid.grx[0] < 0:
        if 4 * tick_step < grid.grx[0]:
            tick_arrangement = tick_step * np.arange(nticks)
        else:
            tick_arrangement = tick_step * np.arange(nticks + 1)

    if grid.grx[0] >= 0:
        if 4 * tick_step > grid.grx[-1]:
            tick_arrangement = tick_step * np.arange(nticks)
        else:
            tick_arrangement = tick_step * np.arange(nticks + 1)

    return tick_arrangement


def detrend_rad(traces):
    # TODO: fill this fct
    return traces


def compute_SNR(mog):
    SNR = np.ones(mog.data.ntrace)

    max_amps = np.amax(np.abs(detrend_rad(mog.data.rdata)))
    i = np.nonzero(np.abs(detrend_rad(mog.data.rdata)) == max_amps)[0]

    width = 60

    i1 = i - width / 2
    i2 = i + width / 2
    i1[i1 < 1] = 1
    i2[i2 > mog.data.nptsptrc] = mog.data.nptsptrc

    for n in range(mog.data.ntrace):
        SNR[n] = np.std(mog.data.rdata[i1[n]:i2[n], n]) / np.std(mog.data.rdata[:width, n])

    return SNR


def data_select(data, freq, dt, L=100, threshold=5, medfilt_len=10):

    shape = np.shape(data)
    M = shape[1]
    std_sig = np.zeros(M).T
    ind_data_select = np.zeros(M, dtype=bool).T
    ind_max = np.zeros(M).T
    nb_p = np.round(1 / (dt * freq))
    width = 60
    if medfilt_len > 0:
        data = scipy.signal.medfilt(data)

    for i in range(M):
        ind1        = np.argmax(data[:, i])
        ind_max[i]  = ind1
        ind         = np.arange(ind1 - nb_p, ind1 + 2 * nb_p + 1)

        if ind[0] < 1:
            ind = np.arange(1, ind1 + width)
        elif ind[-1] < 1:
            ind = np.arange(ind1 - width, ind1)

        std_sig[i] = np.std(data[int(ind[0]):int(ind[-1]), i])

    std_noise = np.std(data[-1 - L: -1, :])
    SNR = std_sig / std_noise
    ind_data_select[SNR > threshold] = True

    return SNR


def f():  # test

    nout = nargout()
    print(nout)
    if nout == 1:
        return 1
    elif nout == 2:
        return 1, 2


if __name__ == "__main__":

    f()
    a = f()
    a, b = f()
