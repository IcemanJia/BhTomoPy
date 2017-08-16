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

import sys
from PyQt5 import QtCore, QtWidgets
from borehole import Borehole
import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from mpl_toolkits.mplot3d import axes3d
import time
import database

from sqlalchemy.orm.attributes import flag_modified


class BoreholeUI(QtWidgets.QWidget):

    # ------- Signals ------- #
    bhlogSignal = QtCore.pyqtSignal(str)
    bhUpdateSignal = QtCore.pyqtSignal(list)  # this signal sends the information to update the Tx and Rx comboboxes in MogUI
    bhInfoSignal = QtCore.pyqtSignal(int)     # this signal sends the information to update the number of boreholes in infoUI

    def __init__(self, parent=None):
        super(BoreholeUI, self).__init__()
        self.setWindowTitle("BhTomoPy/Borehole")
        self.initUI()

    def import_bhole(self):
        """
        This method opens a QFileDialog, takes the name that the user has selected and updates the borehole's informations
        """
        filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Import Borehole')[0]
        try:
            if filename:
                self.load_bh(filename)
        except:
            self.bhlogSignal.emit('Error: Borehole file must have *.xyz extension')

    def load_bh(self, filename):

        rname             = filename.split('/')
        rname             = rname[-1]
        rname             = rname.strip('.xyz')
        bh                = Borehole(str(rname))
        database.session.add(bh)
        bh.fdata          = np.loadtxt(filename)
        bh.X              = bh.fdata[0, 0]
        bh.Y              = bh.fdata[0, 1]
        bh.Z              = bh.fdata[0, 2]
        bh.Xmax           = bh.fdata[-1, 0]
        bh.Ymax           = bh.fdata[-1, 1]
        bh.Zmax           = bh.fdata[-1, 2]
        self.update_List_Widget()
        self.bh_list.setCurrentRow(database.session.query(Borehole).count() - 1)
        self.update_List_Edits()
        self.bhlogSignal.emit("{}.xyz has been loaded successfully".format(rname))
        database.modified = True

    def add_bhole(self):
        """
        This method will create an instance of Borehole and initialize it, while showing the value of all its
        attributes in the coordinates edits
        """
        name, ok = QtWidgets.QInputDialog.getText(self, "Borehole creation", "Borehole name")
        if ok:
            bh = Borehole(str(name))
            database.session.add(bh)
            self.update_List_Widget()
            self.bh_list.setCurrentRow(database.session.query(Borehole).count() - 1)
            self.update_List_Edits()
            self.bhlogSignal.emit("{} borehole has been added successfully".format(name))
            database.modified = True

    def update_List_Widget(self):
        """
        Updates the information in the bh_list, then emits the instances contained in boreholes and the
        length of bh_list to DatabaseUI
        """
        self.bh_list.clear()
        for bh in database.session.query(Borehole).all():
            self.bh_list.addItem(bh.name)
        self.bhInfoSignal.emit(len(self.bh_list))
        self.bhUpdateSignal.emit(database.session.query(Borehole).all())  # TODO rework

    def update_List_Edits(self):
        """
        Updates the coordinates edits information with the attributes of the Borehole class instance
        """
        bh = self.current_borehole()
        if bh:
            self.X_edit.setText(str(bh.X))
            self.Y_edit.setText(str(bh.Y))
            self.Z_edit.setText(str(bh.Z))
            self.Xmax_edit.setText(str(bh.Xmax))
            self.Ymax_edit.setText(str(bh.Ymax))
            self.Zmax_edit.setText(str(bh.Zmax))
            self.Z_surf_edit.setText(str(bh.Z_surf))
            if bh.Z_water is None:
                self.Z_water_edit.setText('')
            else:
                self.Z_water_edit.setText(str(bh.Z_water))
        else:
            self.X_edit.setText('0.0')
            self.Y_edit.setText('0.0')
            self.Z_edit.setText('0.0')
            self.Xmax_edit.setText('0.0')
            self.Ymax_edit.setText('0.0')
            self.Zmax_edit.setText('0.0')
            self.Z_surf_edit.setText('0.0')
            self.Z_water_edit.setText('')

    def current_borehole(self):

        borehole = self.bh_list.currentItem()
        if borehole is not None:
            return database.session.query(Borehole).filter(Borehole.name == borehole.text()).first()

    def del_bhole(self):
        """
        Deletes a borehole instance from boreholes
        """
        item = self.current_borehole()
        if item:
            self.bhlogSignal.emit("{} has been deleted".format(item.name))
            database.delete(database, item)

            self.update_List_Widget()
            self.update_List_Edits()

            database.modified = True

    updateHandler = False  # focus may be lost twice due to setFocus and/or the QMessageBox. 'updateHandler' prevents that.

    def update_bhole_data(self):
        """
        Updates the borehole's attributes from the coordinates edits
        """
        if self.updateHandler:
            return

        self.updateHandler = True
        import re

        exp = re.compile("^-?[0-9]+([\.,][0-9]+)?$")  # float number, with or without decimals, and allowing negatives

        for item in (self.X_edit, self.Y_edit, self.Z_edit,
                     self.Xmax_edit, self.Ymax_edit, self.Zmax_edit,
                     self.Z_surf_edit, self.Z_water_edit):

            if item.text() != '' and not exp.match(item.text()):
                self.bhlogSignal.emit("Error: Some edited information is incorrect.")
                item.setFocus()
                QtWidgets.QMessageBox.warning(self, 'Warning', "Some edited information is incorrect. Edit fields cannot contain letters or special characters.",
                                              buttons=QtWidgets.QMessageBox.Ok)
                self.updateHandler = False
                return

            item.setText(item.text().replace(',', '.'))

        self.updateHandler = False

        item = self.current_borehole()
        if item:
            bh                = item
            bh.X              = float(self.X_edit.text())
            bh.Y              = float(self.Y_edit.text())
            bh.Z              = float(self.Z_edit.text())
            bh.Xmax           = float(self.Xmax_edit.text())
            bh.Ymax           = float(self.Ymax_edit.text())
            bh.Zmax           = float(self.Zmax_edit.text())
            bh.Z_surf         = float(self.Z_surf_edit.text())
            if self.Z_water_edit.text() == '':
                bh.Z_water    = None
            else:
                bh.Z_water    = float(self.Z_water_edit.text())
            bh.fdata[0, 0]  = bh.X
            bh.fdata[0, 1]  = bh.Y
            bh.fdata[0, 2]  = bh.Z
            bh.fdata[-1, 0] = bh.Xmax
            bh.fdata[-1, 1] = bh.Ymax
            bh.fdata[-1, 2] = bh.Zmax
            flag_modified(bh, 'fdata')
            database.modified = True

    def plot(self):
        """
        Plots all the Borehole instances in boreholes
        """
        if database.session.query(Borehole).count() != 0:
            self.bholeFig = BoreholeFig()
            self.bholeFig.plot_bholes(database.session.query(Borehole).all())

            for bh in database.session.query(Borehole).all():
                self.bhlogSignal.emit("{}'s trajectory has been plotted".format(bh.name))
            self.bholeFig.show()

    def attenuation_constraints(self):
        """
        Knowing the values of attenuation depending on elevation, we can define the attenuation on the borehole's trajectory
        with the project method and then associate an exactitude value (covariance) to each of them if it is given in the *.con file.
        We then associate the Cont instance to the borehole's acont attribute
        """
        item = self.current_borehole()
        if item:
            acont = Cont()
            filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File')[0]
            rname = filename.split('/')
            rname = rname[-1]
            rname = rname[:-4]
            if ".con" in filename:
                bh = item
                cont = np.loadtxt(filename)

                acont.x, acont.y, acont.z, _ = bh.project(bh.fdata, cont[:, 0])

                acont.x = acont.x.flatten()
                acont.y = acont.y.flatten()
                acont.z = acont.z.flatten()
                acont.valeur = cont[:, 1]

                if np.size(cont, axis=1) == 3:
                    acont.variance = cont[:, 2]
                else:
                    acont.variance = np.zeros(len(cont[:, 1]))

                bh.acont = acont
                self.bhlogSignal.emit("{} Attenuation Constraints have been applied to Borehole {} ".format(rname, bh.name))
                database.modified = True
            else:
                self.bhlogSignal.emit("Error: the file's extension must be *.con")

    def slowness_constraints(self):
        """
        Practically the same method as attenuation_constraints but reversed
        """
        bh = self.current_borehole()
        scont = Cont()
        if bh:
            filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File')[0]
            rname = filename.split('/')
            rname = rname[-1]
            rname = rname[:-4]
            if ".con" in filename:
                cont = np.loadtxt(filename)

                scont.x, scont.y, scont.z, _ = bh.project(bh.fdata, cont[:, 0])

                scont.x = scont.x.flatten()
                scont.y = scont.y.flatten()
                scont.z = scont.z.flatten()
                scont.valeur = 1 / cont[:, 1]

                if np.size(cont, axis=1) == 3:
                    # inversion of a random variable http://math.stackexchange.com/questions/269216/inverse-of-random-variable
                    scont.variance = cont[:, 2] / (cont[:, 1]**4)
                else:
                    scont.variance = np.zeros(len(cont[:, 1]))

                bh.scont = scont
                self.bhlogSignal.emit("{} Slowness Constraints have been applied to Borehole {} ".format(rname, bh.name))
                database.modified = True
            else:
                self.bhlogSignal.emit("Error: the file's extension must be *.con")

    def initUI(self):

        # --- Class For Alignment --- #
        class MyQLabel(QtWidgets.QLabel):
            def __init__(self, label, ha='left', parent=None):
                super(MyQLabel, self).__init__(label, parent)
                if ha == 'center':
                    self.setAlignment(QtCore.Qt.AlignCenter)
                elif ha == 'right':
                    self.setAlignment(QtCore.Qt.AlignRight)
                else:
                    self.setAlignment(QtCore.Qt.AlignLeft)

        # ------- Widget Creation ------- #
        # --- Buttons Set--- #
        btn_Add                  = QtWidgets.QPushButton("Add")
        btn_Remove               = QtWidgets.QPushButton("Remove")
        btn_Import               = QtWidgets.QPushButton("Import")
        btn_Plot                 = QtWidgets.QPushButton("Plot")
        btn_Constraints_veloc    = QtWidgets.QPushButton("Constraints Veloc.")
        btn_Constraints_atten    = QtWidgets.QPushButton("Constraints Atten.")

        # --- list --- #
        self.bh_list             = QtWidgets.QListWidget()

        # --- Labels --- #
        Coord_label              = MyQLabel('Coordinates:', ha='center')
        Collar_label             = MyQLabel('Collar:', ha='center')
        Bottom_label             = MyQLabel('Bottom:', ha='center')
        X_label                  = MyQLabel('X:', ha='right')
        Y_label                  = MyQLabel('Y:', ha='right')
        Elev_label               = MyQLabel('Elevation:', ha='right')
        Elev_surf_label          = QtWidgets.QLabel("Elevation at surface:")
        Elev_water_label         = MyQLabel('Water elevation:', ha='right')

        # --- Edits --- #
        self.X_edit              = QtWidgets.QLineEdit()
        self.Y_edit              = QtWidgets.QLineEdit()
        self.Z_edit              = QtWidgets.QLineEdit()
        self.Xmax_edit           = QtWidgets.QLineEdit()
        self.Ymax_edit           = QtWidgets.QLineEdit()
        self.Zmax_edit           = QtWidgets.QLineEdit()
        self.Z_surf_edit         = QtWidgets.QLineEdit()
        self.Z_water_edit        = QtWidgets.QLineEdit()

        # --- List Actions --- #
        self.bh_list.itemSelectionChanged.connect(self.update_List_Edits)

        # --- Edits Actions --- #
        self.X_edit.editingFinished.connect(self.update_bhole_data)
        self.Y_edit.editingFinished.connect(self.update_bhole_data)
        self.Z_edit.editingFinished.connect(self.update_bhole_data)
        self.Xmax_edit.editingFinished.connect(self.update_bhole_data)
        self.Ymax_edit.editingFinished.connect(self.update_bhole_data)
        self.Zmax_edit.editingFinished.connect(self.update_bhole_data)
        self.Z_surf_edit.editingFinished.connect(self.update_bhole_data)
        self.Z_water_edit.editingFinished.connect(self.update_bhole_data)

        # --- Buttons Actions --- #
        btn_Add.clicked.connect(self.add_bhole)
        btn_Remove.clicked.connect(self.del_bhole)
        btn_Import.clicked.connect(self.import_bhole)
        btn_Plot.clicked.connect(self.plot)
        btn_Constraints_atten.clicked.connect(self.attenuation_constraints)
        btn_Constraints_veloc.clicked.connect(self.slowness_constraints)

        # --- SubWidgets --- #
        # --- Edits and Labels SubWidgets --- #
        sub_E_and_L_widget          = QtWidgets.QWidget()
        sub_E_and_L_grid            = QtWidgets.QGridLayout()
        sub_E_and_L_grid.addWidget(Coord_label, 0, 0, 1, 2)
        sub_E_and_L_grid.addWidget(Collar_label, 0, 2, 1, 2)
        sub_E_and_L_grid.addWidget(Bottom_label, 0, 4, 1, 2)
        sub_E_and_L_grid.addWidget(X_label, 1, 0, 1, 2)
        sub_E_and_L_grid.addWidget(self.X_edit, 1, 2, 1, 2)
        sub_E_and_L_grid.addWidget(self.Xmax_edit, 1, 4, 1, 2)
        sub_E_and_L_grid.addWidget(Y_label, 2, 0, 1, 2)
        sub_E_and_L_grid.addWidget(self.Y_edit, 2, 2, 1, 2)
        sub_E_and_L_grid.addWidget(self.Ymax_edit, 2, 4, 1, 2)
        sub_E_and_L_grid.addWidget(Elev_label, 3, 0, 1, 2)
        sub_E_and_L_grid.addWidget(self.Z_edit, 3, 2, 1, 2)
        sub_E_and_L_grid.addWidget(self.Zmax_edit, 3, 4, 1, 2)
        sub_E_and_L_grid.addWidget(Elev_surf_label, 4, 1, 1, 2)
        sub_E_and_L_grid.addWidget(self.Z_surf_edit, 4, 3, 1, 2)
        sub_E_and_L_grid.addWidget(Elev_water_label, 5, 1, 1, 2)
        sub_E_and_L_grid.addWidget(self.Z_water_edit, 5, 3, 1, 2)
        sub_E_and_L_widget.setLayout(sub_E_and_L_grid)

        # --- Upper Buttons --- #
        sub_upper_buttons_widget = QtWidgets.QWidget()
        sub_upper_buttons_Grid   = QtWidgets.QGridLayout()
        sub_upper_buttons_Grid.addWidget(btn_Add, 0, 0)
        sub_upper_buttons_Grid.addWidget(btn_Remove, 0, 1)
        sub_upper_buttons_Grid.addWidget(btn_Import, 0, 2)
        sub_upper_buttons_Grid.addWidget(btn_Plot, 0, 3)
        sub_upper_buttons_Grid.setContentsMargins(0, 0, 0, 0)
        sub_upper_buttons_widget.setLayout(sub_upper_buttons_Grid)

        # --- Lower Buttons --- #
        sub_lower_buttons_widget = QtWidgets.QWidget()
        sub_lower_buttons_Grid   = QtWidgets.QGridLayout()
        sub_lower_buttons_Grid.addWidget(btn_Constraints_veloc, 0, 0)
        sub_lower_buttons_Grid.addWidget(btn_Constraints_atten, 0, 1)
        sub_lower_buttons_Grid.setContentsMargins(0, 0, 0, 0)
        sub_lower_buttons_widget.setLayout(sub_lower_buttons_Grid)

        # ------- Grid Disposition ------- #
        master_grid     = QtWidgets.QGridLayout()
        master_grid.addWidget(sub_upper_buttons_widget, 0, 0)
        master_grid.addWidget(self.bh_list, 1, 0)
        master_grid.addWidget(sub_E_and_L_widget, 2, 0)
        master_grid.addWidget(sub_lower_buttons_widget, 4, 0)
        master_grid.setContentsMargins(0, 0, 0, 0)

        # ------- set Layout ------- #
        self.setLayout(master_grid)


class BoreholeFig(FigureCanvasQTAgg):

    def __init__(self):
        """
        Here we create a 3D figure in which we will plot the Borehole instances' trajectory (i.e. their respective fdata)
        """

        fig_width, fig_height = 6, 8
        fig = mpl.figure.Figure(figsize=(fig_width, fig_height), facecolor='white')
        super(BoreholeFig, self).__init__(fig)
        self.initFig()

    def initFig(self):
        ax = self.figure.add_axes([0.05, 0.05, 0.9, 0.9], projection='3d')
        ax.set_axisbelow(True)

    def plot_bholes(self, bhole_list):
        ax = self.figure.axes[0]
        ax.cla()
        for bhole in bhole_list:
            ax.plot(bhole.fdata[:, 0], bhole.fdata[:, 1], bhole.fdata[:, 2], label=bhole.name)

        l = ax.legend(ncol=1, bbox_to_anchor=(0, 1), loc='upper left', borderpad=0)
        l.draw_frame(False)

        self.draw()


class Cont(object):
    """
    This class represents either the slowness constraints(i.e. bh.scont) or the attenuation constraints(i.e. bh.acont).
    We created a class for Cont because it has its own attributes.
    """
    def __init__(self):
        self.x = np.array([])
        self.y = np.array([])
        self.z = np.array([])
        self.valeur = np.array([])
        self.variance = np.array([])


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)

    bh_ui = BoreholeUI()
    bh_ui.show()

    sys.exit(app.exec_())
