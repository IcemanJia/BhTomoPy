# -*- coding: utf-8 -*-
"""
Copyright 2017 Bernard Giroux, Elie Dumas-Lefebvre, Jerome Simon
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

import numpy as np
from sqlalchemy import Column, String, Table, ForeignKey, PickleType
from utils import Base
from sqlalchemy.orm import relationship


# Relationship definition

model_mogs = Table('model_mogs', Base.metadata,
                   Column('Mog_name', String, ForeignKey('Mog.name')),
                   Column('Model_name', String, ForeignKey('Model.name')))


class Model(Base):

    __tablename__ = "Model"
    name       = Column(String, primary_key=True)  # Model's name
    grid       = Column(PickleType)    # Model's grid
    tt_covar   = Column(PickleType)    # Model's Traveltime covariance model
    amp_covar  = Column(PickleType)    # Model's Amplitude covariance model
    inv_res    = Column(PickleType)    # Results of inversion
    tlinv_res  = Column(PickleType)    # Time-lapse inversion results

    mogs = relationship("Mog", secondary=model_mogs)  # The mogs associated with the model (acts like a list).

    @property
    def boreholes(self):
        """
        Returns a list of all the boreholes contained in the mogs of a model, without duplicates.
        """
        boreholes = []

        for mog in self.mogs:
            for borehole in mog.Tx, mog.Rx:
                if borehole is not None:
                    if borehole not in boreholes:  # guarantees there is no duplicate
                        boreholes.append(borehole)

        return boreholes

    def __init__(self, name=''):
        self.name       = name
        self.grid       = None
        self.tt_covar   = None
        self.amp_covar  = None
        self.inv_res    = []
        self.tlinv_res  = None

    @staticmethod
    def getModelData(model, selected_mogs, type1, vlim = 0, type2=''):
        data = np.array([])
        ind = np.array([])
        type2 = ''

        tt = np.array([])
        et = np.array([])
        in_vect = np.array([])
        mogs = []
        for i in selected_mogs:
            mogs.append(model.mogs[i])

        if type1 == 'tt':
            fac_dt = 1

            mog = mogs[0]
            ind = np.not_equal(mog.tt, -1).T
            tt, t0 = mog.getCorrectedTravelTimes()
            tt = tt.T
            et = fac_dt * mog.f_et * mog.et.T
            in_vect = mog.in_vect.T
            no = np.arange(mog.data.ntrace).T

            if len(mogs) > 1:
                for n in range(1, len(model.mogs)):
                    mog = mogs[n]
                    ind = np.concatenate((ind, np.not_equal(mog.tt, -1).T), axis=0)
                    tt = np.concatenate((tt, mog.getCorrectedTravelTimes()[0].T), axis=0)
                    et = np.concatenate((et, fac_dt * mog.et * mog.f_et.T), axis=0)
                    in_vect = np.concatenate((in_vect, mog.in_vect.T), axis=0)
                    no = np.concatenate((no, np.arange(mog.ntrace + 1).T), axis=0)

        elif type1 == "amp":
            mog = mogs[0]
            ind = np.not_equal(mog.tauApp, -1).T
            tt = mog.tauApp.T
            et = mog.tauApp_et.T * mog.f_et
            in_vect = mog.in_vect.T
            no = np.arange(mog.data.ntrace).T

            if len(mogs) > 1:
                for n in range(1, len(model.mogs)):
                    mog = mogs[n]
                    ind = np.concatenate((ind, np.not_equal(mog.tauApp, -1).T), axis=0)
                    tt = np.concatenate((tt, mog.tauApp.T), axis=0)
                    et = np.concatenate((et, mog.tauApp_et.T * mog.f_et), axis=0)
                    in_vect = np.concatenate((in_vect, mog.in_vect.T), axis=0)
                    no = np.concatenate((no, np.arange(mog.ntrace + 1).T), axis=0)

        elif type1 == "fce":
            mog = mogs[0]
            ind = np.not_equal(mog.tauFce, -1).T
            tt = mog.tauFce.T
            et = mog.tauFce_et.T * mog.f_et
            in_vect = mog.in_vect.T
            no = np.arange(mog.data.ntrace).T

            if len(mogs) > 1:
                for n in range(1, len(model.mogs)):
                    mog = mogs[n]
                    ind = np.concatenate((ind, np.not_equal(mog.tauFce, -1).T), axis=0)
                    tt = np.concatenate((tt, mog.tauFce.T), axis=0)
                    et = np.concatenate((et, mog.tauFce_et.T * mog.f_et), axis=0)
                    in_vect = np.concatenate((in_vect, mog.in_vect.T), axis=0)
                    no = np.concatenate((no, np.arange(mog.ntrace + 1).T), axis=0)

        elif type1 == "hyb":
            mog = mogs[0]
            ind = np.not_equal(mog.tauHyb, -1).T
            tt = mog.tauHyb.T
            et = mog.tauHyb_et.T * mog.f_et
            in_vect = mog.in_vect.T
            no = np.arange(mog.data.ntrace).T

            if len(mogs) > 1:
                for n in range(1, len(model.mogs)):
                    mog = mogs[n]
                    ind = np.concatenate((ind, np.not_equal(mog.tauHyb, -1).T), axis=0)
                    tt = np.concatenate((tt, mog.tauHyb.T), axis=0)
                    et = np.concatenate((et, mog.tauHyb_et.T * mog.f_et), axis=0)
                    in_vect = np.concatenate((in_vect, mog.in_vect.T), axis=0)
                    no = np.concatenate((no, np.arange(mog.ntrace + 1).T), axis=0)


        if type2 == 'depth':
            data, ind = getModelData(model, air, selected_mogs, type1)  # @UndefinedVariable
            mog = mogs[0]
            tt = mog.Tx_z_orig.T
            et = mog.Rx_z_orig.T
            in_vect = mog.in_vect.T
            if len(mogs) > 1:
                for n in (1, len(mogs)):
                    tt = np.concatenate((tt, mogs[n].Tx_z_orig.T), axis=0)
                    et = np.concatenate((et, mogs[n].Rx_z_orig.T), axis=0)
                    in_vect = np.concatenate((in_vect, mogs[n].in_vect.T), axis=0)

        if vlim != 0:   
            l = ((model.grid.Tx-model.grid.Rx)**2+2).T
            vapp = l/tt
            in2 = vapp<vlim
            #disp([num2str(sum(~in2&ind)),' rays with apparent velocity above ',num2str(vlim)])
            ind = ind & in2
         
        ind = np.equal((ind.astype(int) + in_vect.astype(int)), 2)
        data = np.array([tt[ind], et[ind], no[ind]]).T
        return data, ind