# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QT
import numpy as np
import matplotlib as mpl
from model import Model
import scipy as spy
from scipy.sparse import linalg
import pickle
from mpl_toolkits.axes_grid1 import make_axes_locatable

class InversionUI(QtGui.QFrame):
    def __init__(self, parent=None):
        super(InversionUI, self).__init__()
        self.setWindowTitle("bh_thomoPy/Inversion")
        self.openmain = OpenMainData(self)
        self.lsqrParams = InvLSQRParams()
        self.mogs = []
        self.boreholes = []
        self.models = []
        self.air = []
        self.filename = ''
        self.model_ind = ''
        self.initUI()
        self.initinvUI()

    def savefile(self):
        save_file = open(self.filename, 'wb')
        self.models[self.model_ind].inv_res = self.tomo
        pickle.dump((self.boreholes, self.mogs, self.air, self.models), save_file)
        dialog = QtGui.QMessageBox.information(self, 'Success', "Database was saved successfully"
                                                ,buttons=QtGui.QMessageBox.Ok)
    def update_data(self):
        for mog in self.models[self.model_ind].mogs:
            self.mog_list.addItem(mog.name)
        self.mog_list.setCurrentRow(0)

    def update_grid(self):
        model = self.models[self.model_ind]
        if np.all(model.grid.grx == 0) or np.all(model.grid.grx == 0):
            dialog = QtGui.QMessageBox.warning(self, 'Warning', "Please create a Grid before Inversion"
                                                ,buttons=QtGui.QMessageBox.Ok)

        else:
            self.X_min_label.setText(str(np.round(model.grid.grx[0], 3)))
            self.X_max_label.setText(str(np.round(model.grid.grx[-1], 3)))
            self.step_Xi_label.setText(str(model.grid.dx()))

            self.Z_min_label.setText(str(np.round(model.grid.grz[0], 3)))
            self.Z_max_label.setText(str(np.round(model.grid.grz[-1], 3)))
            self.step_Zi_label.setText(str(model.grid.dz()))

            if model.grid.type == '3D':
                self.Y_min_label.setText(str(np.round(model.grid.gry[0], 3)))
                self.Y_max_label.setText(str(np.round(model.grid.gry[-1], 3)))
                self.step_Yi_label.setText(str(model.grid.dy()))

            self.num_cells_label.setText(str(model.grid.getNumberOfCells()))

    def update_params(self):
        self.lsqrParams.selectedMogs = self.mog_list.selectedIndexes()
        self.lsqrParams.numItStraight = int(self.straight_ray_edit.text())
        self.lsqrParams.numItCurved = int(self.curv_ray_edit.text())
        self.lsqrParams.useCont = self.use_const_checkbox.isChecked()
        self.lsqrParams.tol = float(self.solver_tol_edit.text())
        self.lsqrParams.wCont = float(self.constraints_weight_edit.text())
        self.lsqrParams.alphax = float(self.smoothing_weight_x_edit.text())
        self.lsqrParams.alphay = float(self.smoothing_weight_y_edit.text())
        self.lsqrParams.alphaz = float(self.smoothing_weight_z_edit.text())
        self.lsqrParams.order = int(self.smoothing_order_combo.currentText())
        self.lsqrParams.nbreiter = float(self.max_iter_edit.text())
        self.lsqrParams.dv_max = 0.01*float(self.veloc_var_edit.text())

    def doInv(self):
        model = self.models[self.model_ind]
        if self.model_ind == '':
            dialog = QtGui.QMessageBox.warning(self, 'Warning', "First, load a model in order to do Inversion"
                                                    , buttons=QtGui.QMessageBox.Ok)

        if len(self.mog_list.selectedIndexes()) == 0:
            dialog = QtGui.QMessageBox.warning(self, 'Warning', "Please select Mogs"
                                                        , buttons=QtGui.QMessageBox.Ok)

        elif self.T_and_A_combo.currentText() == 'Traveltime':
            self.lsqrParams.tomoAtt = 0
            data, idata = Model.getModelData(model, self.air, self.lsqrParams.selectedMogs, 'tt')
            data = np.concatenate((model.grid.Tx[idata, :], model.grid.Rx[idata, :], data, model.grid.TxCosDir[idata, :], model.grid.RxCosDir[idata, :]), axis=1)


        L = np.array([])
        rays = np.array([])

        #TODO
        if self.use_Rays_checkbox.isChecked():
            # Change L and Rays
            pass

        if self.algo_combo.currentText() == 'LSQR Solver':
            self.update_params()
            self.invLSQR(self.lsqrParams, data, idata, model.grid, L)


    def invLSQR(self, params, data, idata, grid, L):
        self.tomo = Tomo()

        if data.shape[1] >= 9:
            self.tomo.no_trace = data[:, 8]

        if np.all(L == 0):
             L = grid.getForwardStraightRays(idata)

        self.tomo.x = 0.5*(grid.grx[0:-2] + grid.grx[1:-1])
        self.tomo.z = 0.5*(grid.grz[0:-2] + grid.grz[1:-1])

        if not np.all(grid.gry == 0):
            self.tomo.y = 0.5*(grid.gry[0:-2] + grid.gry[1:-1])
        else:
            self.tomo.y = np.array([])

        cont = np.array([])
        #TODO:  Ajouter les conditions par rapport au contraintes de vélocité appliquées dans grid editor



        Dx, Dy, Dz = grid.derivative(params.order)

        for noIter in range(params.numItCurved + params.numItStraight):
            self.noIter = noIter
            app.processEvents()

            if noIter == 0:
                l_moy = np.mean(data[:, 6]/ L.sum(axis= 1))
            else:
                l_moy = np.mean(self.tomo.s)

            # We make sur to have a b array whit (m,) shape
            mta = L.sum(axis= 1)*l_moy
            mta = np.hstack(mta).T

            tmp = mta.flat
            tmp = list(tmp)

            mta = np.asarray(tmp)

            dt = data[:, 6] - mta
            dt = dt.T

            if noIter == 0:
                s_o = l_moy * np.ones(L.shape[1]).T

            #A = np.array([[L],
            #              [Dx*params.alphax],
            #              [Dy*params.alphay],
            #              [Dz*params.alphaz]])

            #b = np.array([dt, np.zeros((Dx.shape[0], 1)), np.zeros((Dy.shape[0], 1)), np.zeros((Dz.shape[0], 1))])

            A = L
            b = dt


            if not np.all(cont == 0) and params.useCont == 1:
                #TODO
                pass

            ans = linalg.lsqr(A, b, atol= params.tol, btol= params.tol, iter_lim = params.nbreiter)
            x = ans[0]

            if noIter == 0:
                self.tomo.res[0] = ans[3]
            else:
                np.append(self.tomo.res, ans[3])


            if max(abs(s_o/(x+l_moy) - 1)) > params.dv_max:
                fac = min(abs( (s_o/(params.dv_max+1)-l_moy)/x ))
                x = fac*x
                s_o = x + l_moy

            self.tomo.s = x + l_moy

            tt,L,self.tomo.rays = grid.raytrace(self.tomo.s, data[:, 0:3], data[:, 3:6])


            self.algo_label.setText('LSQR Inversion -')
            self.noIter_label.setText('Ray Tracing, Iteration {}'.format(noIter+1))
            self.invFig.plot_inv()

            if params.saveInvData == 1:
                tt = L * self.tomo.s
                if noIter == 0:
                    self.tomo.invData.res = np.array([data[:, 6] - tt]).T
                    self.tomo.invData.s = np.array([self.tomo.s]).T

                else:

                    self.tomo.invData.res = np.concatenate((self.tomo.invData.res, np.array([data[:, 6] - tt]).T), axis= 1)

                    self.tomo.invData.s = np.concatenate((self.tomo.invData.s, np.array([self.tomo.s]).T), axis= 1)

            self.tomo.L = L

        self.algo_label.setText('LSQR Inversion -')
        self.noIter_label.setText('Finished, {} Iterations Done'.format(noIter+1))


    def plot_rays(self):
        self.raysFig.plot_rays()
        self.rays_manager.show()

    def plot_ray_density(self):
        self.raydensityFig.plot_ray_density()
        self.ray_density_manager.show()

    def plot_residuals(self):
        self.residualsFig.plot_residuals()
        self.residuals_manager.showMaximized()

    def plot_tomo(self):
        self.tomoFig.plot_tomo()
        self.tomo_manager.show()

    def initinvUI(self):

        #------- Widget Creation -------#
        #--- Labels ---#
        num_simulation_label        = MyQLabel("Number of Simulations", ha='right')
        slowness_label              = MyQLabel("Slowness", ha='right')
        islowness_label              = MyQLabel("Slowness", ha='center')
        separ_label                 = MyQLabel("|", ha= 'center')
        traveltime_label            = MyQLabel("Traveltime", ha= 'right')
        solver_tol_label            = MyQLabel('Solver Tolerance', ha= 'right')
        max_iter_label              = MyQLabel('Max number of solver iterations', ha= 'right')
        constraints_weight_label    = MyQLabel('Constraints weight', ha= 'right')
        smoothing_weight_x_label    = MyQLabel('Smoothing weight x', ha= 'right')
        smoothing_weight_y_label    = MyQLabel('Smoothing weight y', ha= 'right')
        smoothing_weight_z_label    = MyQLabel('Smoothing weight z', ha= 'right')
        smoothing_order_label       = MyQLabel('Smoothing operator order', ha= 'right')
        veloc_var_label             = MyQLabel('Max velocity varitation per iteration[%]', ha= 'right')
        range_x_label = MyQLabel('Range X', ha= 'right')
        range_z_label = MyQLabel('Range Z', ha= 'right')
        theta_x_label = MyQLabel('theta X', ha= 'right')
        sill_label = MyQLabel('Sill', ha= 'right')


        #--- Edits ---#
        self.num_simulation_edit     = QtGui.QLineEdit('128')
        self.slowness_edit           = QtGui.QLineEdit('0')
        self.traveltime_edit         = QtGui.QLineEdit('0')
        self.solver_tol_edit         = QtGui.QLineEdit('1e-6')
        self.max_iter_edit           = QtGui.QLineEdit('100')
        self.constraints_weight_edit = QtGui.QLineEdit('1')
        self.smoothing_weight_x_edit = QtGui.QLineEdit('10')
        self.smoothing_weight_y_edit = QtGui.QLineEdit('10')
        self.smoothing_weight_z_edit = QtGui.QLineEdit('10')
        self.veloc_var_edit          = QtGui.QLineEdit('50')

        self.range_x_edit = QtGui.QLineEdit()
        self.range_z_edit = QtGui.QLineEdit()
        self.theta_x_edit = QtGui.QLineEdit()
        self.sill_edit = QtGui.QLineEdit()

        #- Edits' Disposition -#
        self.num_simulation_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.slowness_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.traveltime_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.solver_tol_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.max_iter_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.constraints_weight_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.smoothing_weight_x_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.smoothing_weight_y_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.smoothing_weight_z_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.veloc_var_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.range_x_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.range_z_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.theta_x_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.sill_edit.setAlignment(QtCore.Qt.AlignHCenter)

        self.num_simulation_edit.setFixedWidth(100)
        self.slowness_edit.setFixedWidth(100)
        self.traveltime_edit.setFixedWidth(100)
        self.solver_tol_edit.setFixedWidth(100)
        self.max_iter_edit.setFixedWidth(100)
        self.constraints_weight_edit.setFixedWidth(100)
        self.smoothing_weight_x_edit.setFixedWidth(100)
        self.smoothing_weight_y_edit.setFixedWidth(100)
        self.smoothing_weight_z_edit.setFixedWidth(100)
        self.veloc_var_edit.setFixedWidth(100)

        #- Edits Actions -#
        self.num_simulation_edit.editingFinished.connect(self.update_params)
        self.slowness_edit.editingFinished.connect(self.update_params)
        self.traveltime_edit.editingFinished.connect(self.update_params)
        self.solver_tol_edit.editingFinished.connect(self.update_params)
        self.max_iter_edit.editingFinished.connect(self.update_params)
        self.constraints_weight_edit.editingFinished.connect(self.update_params)
        self.smoothing_weight_x_edit.editingFinished.connect(self.update_params)
        self.smoothing_weight_y_edit.editingFinished.connect(self.update_params)
        self.smoothing_weight_z_edit.editingFinished.connect(self.update_params)
        self.veloc_var_edit.editingFinished.connect(self.update_params)

        #--- CheckBoxes ---#
        include_checkbox                = QtGui.QCheckBox("Include Experimental Variance")
        tilted_ellip_veloc_checkbox     = QtGui.QCheckBox("Tilted Elliptical Velocity Anisotropy")
        simulations_checkbox            = QtGui.QCheckBox("Simulations")
        ellip_veloc_checkbox            = QtGui.QCheckBox("Elliptical Velocity Anisotropy")

        #--- ComboBoxes ---#
        self.geostat_struct_combo     = QtGui.QComboBox()
        self.smoothing_order_combo = QtGui.QComboBox()
        self.param_combo = QtGui.QComboBox()

        #- Comboboxes Actions -#
        self.smoothing_order_combo.activated.connect(self.update_params)

        #--- List ---#
        test_list                = QtGui.QListWidget()     #list for the Parameters Groupbox

        #--- Combobox's Items ---#
        params = ['Cubic', 'Sperical', 'Gaussian', 'Exponential', 'Linear', 'Thin Plate', 'Gravimetric', 'Magnetic', 'Hole Effect Sine', 'Hole Effect Cosine']
        self.param_combo.addItems(params)
        self.geostat_struct_combo.addItem("Structure no 1")
        self.smoothing_order_combo.addItems(['1', '2'])


        #--- Slowness Frame ---#
        slownessFrame = QtGui.QFrame()
        slownessGrid = QtGui.QGridLayout()
        slownessGrid.addWidget(islowness_label)
        slownessFrame.setLayout(slownessGrid)

        #--- Param SubWidget ---#
        sub_param_widget = QtGui.QWidget()
        sub_param_grid = QtGui.QGridLayout()
        sub_param_grid.addWidget(slownessFrame, 0, 1)
        sub_param_grid.addWidget(self.param_combo, 1, 1)
        sub_param_grid.addWidget(range_x_label, 2, 0)
        sub_param_grid.addWidget(range_z_label, 3, 0)
        sub_param_grid.addWidget(theta_x_label, 4, 0)
        sub_param_grid.addWidget(sill_label, 5, 0)
        sub_param_grid.addWidget(self.range_x_edit, 2, 1)
        sub_param_grid.addWidget(self.range_z_edit, 3, 1)
        sub_param_grid.addWidget(self.theta_x_edit, 4, 1)
        sub_param_grid.addWidget(self.sill_edit, 5, 1)
        sub_param_widget.setLayout(sub_param_grid)

        #--- Scroll Area which contains the Geostatistical Parameters ---#
        scrollArea = QtGui.QScrollArea()
        scrollArea.setBackgroundRole(QtGui.QPalette.Dark)
        scrollArea.setWidget(sub_param_widget)

        #--- Parameters Groupbox ---#
        Param_groupbox = QtGui.QGroupBox("Parameters")
        Param_grid = QtGui.QGridLayout()
        Param_grid.addWidget(scrollArea, 0, 0)
        Param_grid.setVerticalSpacing(0)
        Param_groupbox.setLayout(Param_grid)

        #--- Nugget Effect Groupbox ---#
        Nug_groupbox = QtGui.QGroupBox("Nugget Effect")
        Nug_grid = QtGui.QGridLayout()
        Nug_grid.addWidget(slowness_label, 0, 0)
        Nug_grid.addWidget(self.slowness_edit, 0, 1)
        Nug_grid.addWidget(separ_label, 0, 3)
        Nug_grid.addWidget(traveltime_label, 0, 4)
        Nug_grid.addWidget(self.traveltime_edit, 0, 5)
        Nug_groupbox.setLayout(Nug_grid)

         #--- Geostatistical inversion Groupbox ---#
        Geostat_groupbox = QtGui.QGroupBox("Geostatistical inversion")
        Geostat_grid = QtGui.QGridLayout()
        Geostat_grid.addWidget(simulations_checkbox, 0, 0)
        Geostat_grid.addWidget(ellip_veloc_checkbox, 1, 0)
        Geostat_grid.addWidget(include_checkbox, 2, 0)
        Geostat_grid.addWidget(num_simulation_label, 0, 1)
        Geostat_grid.addWidget(self.num_simulation_edit, 0, 2)
        Geostat_grid.addWidget(tilted_ellip_veloc_checkbox, 1, 1)
        Geostat_grid.addWidget(self.geostat_struct_combo, 2, 1, 1, 2)
        Geostat_grid.addWidget(Param_groupbox, 3, 0, 1, 3)
        Geostat_grid.addWidget(Nug_groupbox, 4, 0, 1, 3)
        Geostat_grid.setRowStretch(3, 100)
        Geostat_groupbox.setLayout(Geostat_grid)

        #--- LSQR Solver GroupBox ---#
        LSQR_group = QtGui.QGroupBox('LSQR Solver')
        LSQR_grid = QtGui.QGridLayout()
        LSQR_grid.addWidget(solver_tol_label, 0, 0)
        LSQR_grid.addWidget(max_iter_label, 1, 0)
        LSQR_grid.addWidget(constraints_weight_label, 2, 0)
        LSQR_grid.addWidget(smoothing_weight_x_label, 3, 0)
        LSQR_grid.addWidget(smoothing_weight_y_label, 4, 0)
        LSQR_grid.addWidget(smoothing_weight_z_label, 5, 0)
        LSQR_grid.addWidget(smoothing_order_label, 6, 0)
        LSQR_grid.addWidget(veloc_var_label, 7, 0)
        LSQR_grid.addWidget(self.solver_tol_edit, 0, 1)
        LSQR_grid.addWidget(self.max_iter_edit, 1, 1)
        LSQR_grid.addWidget(self.constraints_weight_edit, 2, 1)
        LSQR_grid.addWidget(self.smoothing_weight_x_edit, 3, 1)
        LSQR_grid.addWidget(self.smoothing_weight_y_edit, 4, 1)
        LSQR_grid.addWidget(self.smoothing_weight_z_edit, 5, 1)
        LSQR_grid.addWidget(self.smoothing_order_combo, 6, 1)
        LSQR_grid.addWidget(self.veloc_var_edit, 7, 1)
        LSQR_group.setLayout(LSQR_grid)

        if self.algo_combo.currentText() == 'LSQR Solver':
            current = self.Inv_Param_grid.layout()
            widget = current.itemAtPosition(2, 0).widget()

            widget.setHidden(True)
            self.Inv_Param_grid.removeWidget(widget)

            self.Inv_Param_grid.addWidget(LSQR_group, 2, 0, 1, 3)
            self.repaint()

        else:
            current = self.Inv_Param_grid.layout()
            widget = current.itemAtPosition(2, 0).widget()
            widget.setHidden(True)
            self.Inv_Param_grid.removeWidget(widget)
            self.Inv_Param_grid.addWidget(Geostat_groupbox, 2, 0, 1, 3)
            self.repaint()

    def initUI(self):

        #-------- Manager for InvFig -------#
        self.invFig = InvFig(self)
        self.invtool = NavigationToolbar2QT(self.invFig, self)
        self.invmanager = QtGui.QWidget()
        inv_grid = QtGui.QGridLayout()
        inv_grid.addWidget(self.invtool, 0, 0)
        inv_grid.addWidget(self.invFig, 1, 0)
        inv_grid.setContentsMargins(0, 0, 0, 0)
        inv_grid.setVerticalSpacing(0)
        self.invmanager.setLayout(inv_grid)

        #-------Manager for RaysFig ------#
        self.raysFig = RaysFig(self)
        self.raystool = NavigationToolbar2QT(self.raysFig, self)
        self.rays_manager = QtGui.QWidget()
        rays_grid = QtGui.QGridLayout()
        rays_grid.addWidget(self.raystool, 0, 0)
        rays_grid.addWidget(self.raysFig, 1, 0)
        self.rays_manager.setLayout(rays_grid)

        #-------Manager for RaysFig ------#
        self.raydensityFig = RayDensityFig(self)
        self.raydensitytool = NavigationToolbar2QT(self.raydensityFig, self)
        self.ray_density_manager = QtGui.QWidget()
        ray_density_grid = QtGui.QGridLayout()
        ray_density_grid.addWidget(self.raydensitytool, 0, 0)
        ray_density_grid.addWidget(self.raydensityFig, 1, 0)
        self.ray_density_manager.setLayout(ray_density_grid)

        #-------Manager for ResidualsFig ------#
        self.residualsFig = ResidualsFig(self)
        self.residualstool = NavigationToolbar2QT(self.residualsFig, self)
        self.residuals_manager = QtGui.QWidget()
        residuals_grid = QtGui.QGridLayout()
        residuals_grid.addWidget(self.residualstool, 0, 0)
        residuals_grid.addWidget(self.residualsFig, 1, 0)
        self.residuals_manager.setLayout(residuals_grid)

        #-------Manager for TomoFig ------#
        self.tomoFig = TomoFig(self)
        self.tomotool = NavigationToolbar2QT(self.tomoFig, self)
        self.tomo_manager = QtGui.QWidget()
        tomo_grid = QtGui.QGridLayout()
        tomo_grid.addWidget(self.tomotool, 0, 0)
        tomo_grid.addWidget(self.tomoFig, 1, 0)
        self.tomo_manager.setLayout(tomo_grid)


        #--- Color for the labels ---#
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Foreground, QtCore.Qt.red)

        #------- Widgets Creation -------#
        #--- Buttons Set ---#
        btn_View        = QtGui.QPushButton("Show Stats")
        btn_Delete      = QtGui.QPushButton("Add Structure")
        btn_Load        = QtGui.QPushButton("Remove Structure")
        btn_GO          = QtGui.QPushButton("GO")

        #- Buttons Action -#
        btn_GO.clicked.connect(self.doInv)

        #--- Label ---#
        model_label                 = MyQLabel("Model :", ha= 'center')
        cells_label                 = MyQLabel("Cells", ha= 'center')
        mog_label                   = MyQLabel("Select Mog", ha= 'center')
        Min_label                   = MyQLabel("Min", ha= 'right')
        Max_label                   = MyQLabel("Max", ha='right')
        Min_labeli                  = MyQLabel("Min :", ha= 'right')
        Max_labeli                  = MyQLabel("Max :", ha='right')
        X_label                     = MyQLabel("X", ha= 'center')
        Y_label                     = MyQLabel("Y", ha= 'center')
        Z_label                     = MyQLabel("Z", ha= 'center')
        algo_label                  = MyQLabel("Algorithm", ha= 'right')
        straight_ray_label          = MyQLabel("Straight Rays", ha= 'right')
        curv_ray_label              = MyQLabel("Curved Rays", ha= 'right')
        step_label                  = MyQLabel("Step :", ha= 'center')
        Xi_label                    = MyQLabel("X", ha= 'center')          # The Xi, Yi and Zi  QLabels are practically the
        Yi_label                    = MyQLabel("Y", ha= 'center')          # same as the X, Y and Z  QLabels, it's just that
        Zi_label                    = MyQLabel("Z", ha= 'center')          # QtGui does not allow to use the same QLabel
                                                                           # twice or more. So we had to create new Qlabels

        # These Labels are bein set as attributes of the InversionUI class because they need to be modified
        # depending on the model's informations
        self.X_min_label            = MyQLabel("0", ha= 'center')
        self.Y_min_label            = MyQLabel("0", ha= 'center')
        self.Z_min_label            = MyQLabel("0", ha= 'center')
        self.X_max_label            = MyQLabel("0", ha= 'center')
        self.Y_max_label            = MyQLabel("0", ha= 'center')
        self.Z_max_label            = MyQLabel("0", ha= 'center')
        self.step_Xi_label          = MyQLabel("0", ha= 'center')
        self.step_Yi_label          = MyQLabel("0", ha= 'center')
        self.step_Zi_label          = MyQLabel("0", ha= 'center')
        self.num_cells_label        = MyQLabel("0", ha= 'center')
        self.algo_label             = MyQLabel('', ha= 'right')
        self.noIter_label           = MyQLabel('', ha= 'left')

        #--- Setting Label's color ---#
        self.num_cells_label.setPalette(palette)
        self.X_min_label.setPalette(palette)
        self.Y_min_label.setPalette(palette)
        self.Z_min_label.setPalette(palette)
        self.X_max_label.setPalette(palette)
        self.Y_max_label.setPalette(palette)
        self.Z_max_label.setPalette(palette)
        self.step_Xi_label.setPalette(palette)
        self.step_Yi_label.setPalette(palette)
        self.step_Zi_label.setPalette(palette)
        cells_label.setPalette(palette)
        model_label.setPalette(palette)
        self.algo_label.setPalette(palette)
        self.noIter_label.setPalette(palette)

        #--- Edits ---#
        self.straight_ray_edit       = QtGui.QLineEdit("1")  # Putting a string as the argument of the QLineEdit initializes
        self.curv_ray_edit           = QtGui.QLineEdit("1")  # it to the argument
        self.Min_editi               = QtGui.QLineEdit('0.06')
        self.Max_editi               = QtGui.QLineEdit('0.12')

        #- Edits' Disposition -#
        self.straight_ray_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.curv_ray_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.Min_editi.setAlignment(QtCore.Qt.AlignHCenter)
        self.Max_editi.setAlignment(QtCore.Qt.AlignHCenter)

        #- Edits' Actions -#
        self.Min_editi.editingFinished.connect(self.invFig.plot_inv)
        self.Max_editi.editingFinished.connect(self.invFig.plot_inv)

        #--- Checkboxes ---#
        self.use_const_checkbox              = QtGui.QCheckBox("Use Constraints")  # The argument of the QCheckBox is the title
        self.use_Rays_checkbox               = QtGui.QCheckBox("Use Rays")         # of it
        self.set_color_checkbox             = QtGui.QCheckBox("Set Color Limits")

        #- Checboxes Actions -#
        self.use_const_checkbox.stateChanged.connect(self.update_params)
        self.set_color_checkbox.stateChanged.connect(self.invFig.plot_inv)

        #--- Actions ---#
        openAction = QtGui.QAction('Open main data file', self)
        openAction.triggered.connect(self.openmain.show)

        saveAction = QtGui.QAction('Save', self)
        saveAction.triggered.connect(self.savefile)

        exportAction = QtGui.QAction('Export', self)

        tomoAction = QtGui.QAction('Tomogram', self)
        tomoAction.triggered.connect(self.plot_tomo)

        simulAction = QtGui.QAction('Simulations', self)

        raysAction = QtGui.QAction('Rays', self)
        raysAction.triggered.connect(self.plot_rays)

        densityAction = QtGui.QAction('Ray Density', self)
        densityAction.triggered.connect(self.plot_ray_density)

        residAction = QtGui.QAction('Residuals', self)
        residAction.triggered.connect(self.plot_residuals)
        #--- ToolBar ---#
        self.tool = QtGui.QMenuBar()
        fileMenu = self.tool.addMenu('&File')
        resultsMenu = self.tool.addMenu('&Results')

        resultsMenu.addActions([exportAction, tomoAction, simulAction, raysAction, densityAction, residAction])

        fileMenu.addAction(openAction)
        fileMenu.addAction(saveAction)

        #--- List ---#
        self.mog_list            = QtGui.QListWidget()

        #- List disposition -#
        self.mog_list.setFixedHeight(50)
        self.mog_list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        #- List Actions -#
        self.mog_list.itemSelectionChanged.connect(self.update_params)

        #--- combobox ---#
        self.T_and_A_combo            = QtGui.QComboBox()
        self.prev_inversion_combo     = QtGui.QComboBox()
        self.algo_combo               = QtGui.QComboBox()
        self.fig_combo                = QtGui.QComboBox()



        #------- Items in the comboboxes --------#
        #--- Time and Amplitude Combobox's Items ---#
        self.T_and_A_combo.addItem("Traveltime")
        self.T_and_A_combo.addItem("Amplitude - Peak-to-Peak")
        self.T_and_A_combo.addItem("Amplitude - Centroid Frequency")

        #--- Algorithm Combobox's Items ---#
        self.algo_combo.addItem("LSQR Solver")
        self.algo_combo.addItem("Geostatistic")

        #- ComboBoxes Action -#
        self.algo_combo.activated.connect(self.initinvUI)
        self.fig_combo.activated.connect(self.invFig.plot_inv)

        #--- Figure's ComboBox's Items ---#

        list1 = ['inferno', 'seismic', 'jet', 'hsv', 'hot',
                 'cool', 'autumn', 'winter', 'spring', 'summer',
                 'gray', 'bone', 'copper', 'pink', 'prism', 'flag']

        self.fig_combo.addItems(list1)


        #------- Frame for number of Iterations -------#
        iterFrame = QtGui.QFrame()
        iterGrid = QtGui.QGridLayout()
        iterGrid.addWidget(self.noIter_label, 0, 1)
        iterGrid.addWidget(self.algo_label, 0, 0)
        iterFrame.setLayout(iterGrid)
        iterFrame.setStyleSheet('background: white')

        #------- SubWidgets -------#
        #--- Algo SubWidget ---#
        Sub_algo_Widget = QtGui.QWidget()
        Sub_algo_Grid = QtGui.QGridLayout()
        Sub_algo_Grid.addWidget(algo_label, 0, 0)
        Sub_algo_Grid.addWidget(self.algo_combo, 0, 1)
        Sub_algo_Grid.setContentsMargins(0, 0, 0, 0)
        Sub_algo_Widget.setLayout(Sub_algo_Grid)

        #---  Grid Coordinates SubWidget ---#
        Sub_Grid_Coord_Widget = QtGui.QWidget()
        Sub_Grid_Coord_grid = QtGui.QGridLayout()
        Sub_Grid_Coord_grid.addWidget(X_label, 0, 1)
        Sub_Grid_Coord_grid.addWidget(Y_label, 0, 2)
        Sub_Grid_Coord_grid.addWidget(Z_label, 0, 3)
        Sub_Grid_Coord_grid.addWidget(Min_label, 1, 0)
        Sub_Grid_Coord_grid.addWidget(Max_label, 2, 0)
        Sub_Grid_Coord_grid.addWidget(self.X_min_label, 1, 1)
        Sub_Grid_Coord_grid.addWidget(self.Y_min_label, 1, 2)
        Sub_Grid_Coord_grid.addWidget(self.Z_min_label, 1, 3)
        Sub_Grid_Coord_grid.addWidget(self.X_max_label, 2, 1)
        Sub_Grid_Coord_grid.addWidget(self.Y_max_label, 2, 2)
        Sub_Grid_Coord_grid.addWidget(self.Z_max_label, 2, 3)
        Sub_Grid_Coord_grid.setContentsMargins(0, 0, 0, 0)
        Sub_Grid_Coord_grid.setVerticalSpacing(3)
        Sub_Grid_Coord_Widget.setLayout(Sub_Grid_Coord_grid)

        #--- Cells SubWidget ---#
        sub_cells_widget = QtGui.QWidget()
        sub_cells_grid = QtGui.QGridLayout()
        sub_cells_grid.addWidget(self.num_cells_label, 0, 0)
        sub_cells_grid.addWidget(cells_label, 0, 1)
        sub_cells_widget.setLayout(sub_cells_grid)

        #--- Step SubWidget ---#
        Sub_Step_Widget = QtGui.QWidget()
        Sub_Step_Grid = QtGui.QGridLayout()
        Sub_Step_Grid.addWidget(step_label, 1, 0)
        Sub_Step_Grid.addWidget(self.step_Xi_label, 1, 1)
        Sub_Step_Grid.addWidget(self.step_Yi_label, 1, 2)
        Sub_Step_Grid.addWidget(self.step_Zi_label, 1, 3)
        Sub_Step_Grid.addWidget(Xi_label, 0, 1)
        Sub_Step_Grid.addWidget(Yi_label, 0, 2)
        Sub_Step_Grid.addWidget(Zi_label, 0, 3)
        Sub_Step_Grid.addWidget(sub_cells_widget, 2, 2)
        Sub_Step_Grid.setContentsMargins(0, 0, 0, 0)
        Sub_Step_Grid.setVerticalSpacing(3)
        Sub_Step_Widget.setLayout(Sub_Step_Grid)

        #--- Straight Rays SubWidget ---#
        sub_straight_widget = QtGui.QWidget()
        sub_straight_grid = QtGui.QGridLayout()
        sub_straight_grid.addWidget(straight_ray_label, 0, 0)
        sub_straight_grid.addWidget(self.straight_ray_edit, 0, 1)
        sub_straight_grid.setContentsMargins(0, 0, 0, 0)
        sub_straight_widget.setLayout(sub_straight_grid)

        #--- Curved Rays SubWidget ---#
        sub_curved_widget = QtGui.QWidget()
        sub_curved_grid = QtGui.QGridLayout()
        sub_curved_grid.addWidget(curv_ray_label, 0, 0)
        sub_curved_grid.addWidget(self.curv_ray_edit, 0, 1)
        sub_curved_grid.setContentsMargins(0, 0, 0, 0)
        sub_curved_widget.setLayout(sub_curved_grid)

        #------- SubGroupboxes -------#
        #--- Data Groupbox ---#
        data_groupbox = QtGui.QGroupBox("Data")
        data_grid = QtGui.QGridLayout()
        data_grid.addWidget(model_label, 0, 0)
        data_grid.addWidget(self.T_and_A_combo, 1, 0)
        data_grid.addWidget(self.use_const_checkbox, 2, 0)
        data_grid.addWidget(mog_label, 0, 2)
        data_grid.addWidget(self.mog_list, 1, 2, 2, 1)
        data_groupbox.setLayout(data_grid)

        #--- Grid Groupbox ---#
        Grid_groupbox = QtGui.QGroupBox("Grid")
        Grid_grid = QtGui.QGridLayout()
        Grid_grid.addWidget(Sub_Grid_Coord_Widget, 0, 0)
        Grid_grid.addWidget(Sub_Step_Widget, 0, 1)
        Grid_groupbox.setLayout(Grid_grid)

        #--- Previous Inversion Groupbox ---#
        prev_inv_groupbox = QtGui.QGroupBox("Previous Inversions")
        prev_inv_grid = QtGui.QGridLayout()
        prev_inv_grid.addWidget(self.prev_inversion_combo, 0, 0, 1, 2)
        prev_inv_grid.addWidget(btn_View, 1, 0)
        prev_inv_grid.addWidget(btn_Delete, 1, 1)
        prev_inv_grid.addWidget(btn_Load, 1, 2)
        prev_inv_grid.addWidget(self.use_Rays_checkbox, 0, 2)
        prev_inv_groupbox.setLayout(prev_inv_grid)

        #--- Number of Iteration Groupbox ---#
        Iter_num_groupbox = QtGui.QGroupBox("Number of Iterations")
        Iter_num_grid = QtGui.QGridLayout()
        Iter_num_grid.addWidget(sub_straight_widget, 0, 0)
        Iter_num_grid.addWidget(sub_curved_widget, 0, 1)
        Iter_num_groupbox.setLayout(Iter_num_grid)

        #--- Inversion Parameters Groupbox ---#
        Inv_Param_groupbox = QtGui.QGroupBox(" Inversion Parameters")
        self.Inv_Param_grid = QtGui.QGridLayout()
        self.Inv_Param_grid.addWidget(Sub_algo_Widget, 0, 0)
        self.Inv_Param_grid.addWidget(Iter_num_groupbox, 1, 0, 1, 3)
        self.Inv_Param_grid.addWidget(QtGui.QLabel('Place Algo Group'), 2, 0, 1, 3)
        self.Inv_Param_grid.addWidget(btn_GO, 3, 1)
        Inv_Param_groupbox.setLayout(self.Inv_Param_grid)

        #--- Figures Groupbox ---#
        fig_groupbox = QtGui.QGroupBox("Figures")
        fig_grid = QtGui.QGridLayout()
        fig_grid.addWidget(self.set_color_checkbox, 0, 0)
        fig_grid.addWidget(Min_labeli, 0, 1)
        fig_grid.addWidget(self.Min_editi, 0, 2)
        fig_grid.addWidget(Max_labeli, 0, 3)
        fig_grid.addWidget(self.Max_editi, 0, 4)
        fig_grid.addWidget(self.fig_combo, 0, 5)
        fig_groupbox.setLayout(fig_grid)

        #--- Figure Groupbox dependent SubWidget ---#
        Sub_right_Widget = QtGui.QWidget()
        Sub_right_Grid = QtGui.QGridLayout()
        Sub_right_Grid.addWidget(fig_groupbox, 0, 0)
        Sub_right_Grid.setContentsMargins(0, 0, 0, 0)
        Sub_right_Widget.setLayout(Sub_right_Grid)

        #------- Global Widget Disposition -------#
        global_widget = QtGui.QWidget()
        self.global_grid = QtGui.QGridLayout()
        self.global_grid.addWidget(data_groupbox, 0, 0, 3, 1)
        self.global_grid.addWidget(Grid_groupbox, 3, 0)
        self.global_grid.addWidget(prev_inv_groupbox, 5, 0)
        self.global_grid.addWidget(Inv_Param_groupbox, 6, 0)
        self.global_grid.addWidget(Sub_right_Widget, 0, 1)
        self.global_grid.addWidget(iterFrame, 0, 2)
        self.global_grid.addWidget(self.invmanager, 1, 1, 7, 2)
        self.global_grid.setColumnStretch(2, 300)
        self.global_grid.setVerticalSpacing(1)
        self.global_grid.setRowStretch(7, 100)
        global_widget.setLayout(self.global_grid)

        #------- Master Grid Disposition -------#
        master_grid = QtGui.QGridLayout()
        master_grid.addWidget(self.tool, 0, 0)
        master_grid.addWidget(global_widget, 1, 0)
        master_grid.setContentsMargins(0, 0, 0, 0)
        self.setLayout(master_grid)

class OpenMainData(QtGui.QWidget):
    def __init__(self, inv, parent=None):
        super(OpenMainData, self).__init__()
        self.setWindowTitle("Choose Data")
        self.database_list = []
        self.inv = inv
        self.initUI()

    def openfile(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Open Database')

        self.load_file(filename)

    def load_file(self, filename):
        self.inv.filename = filename
        rname = filename.split('/')
        rname = rname[-1]
        if '.p' in rname:
            rname = rname[:-2]
        if '.pkl' in rname:
            rname = rname[:-4]
        if '.pickle' in rname:
            rname = rname[:-7]
        file = open(filename, 'rb')

        self.inv.boreholes, self.inv.mogs, self.inv.air, self.inv.models = pickle.load(file)

        self.database_edit.setText(rname)
        for model in self.inv.models:
            self.model_combo.addItem(model.name)


    def cancel(self):
        self.close()

    def ok(self):
        self.inv.model_ind = self.model_combo.currentIndex()
        self.inv.update_data()
        self.inv.update_grid()
        self.close()

    def initUI(self):

        #-------  Widgets --------#
        #--- Edit ---#
        self.database_edit = QtGui.QLineEdit()
        #- Edit Action -#
        self.database_edit.setReadOnly(True)
        #--- Buttons ---#
        self.btn_database = QtGui.QPushButton('Choose Database')
        self.btn_ok = QtGui.QPushButton('Ok')
        self.btn_cancel = QtGui.QPushButton('Cancel')

        #- Buttons' Actions -#
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_database.clicked.connect(self.openfile)
        self.btn_ok.clicked.connect(self.ok)

        #--- Combobox ---#
        self.model_combo = QtGui.QComboBox()

        #- Combobox's Action -#
        master_grid = QtGui.QGridLayout()
        master_grid.addWidget(self.database_edit, 0, 0, 1, 2)
        master_grid.addWidget(self.btn_database, 1, 0, 1, 2)
        master_grid.addWidget(self.model_combo, 2, 0, 1, 2)
        master_grid.addWidget(self.btn_ok, 3, 0)
        master_grid.addWidget(self.btn_cancel, 3 ,1)
        self.setLayout(master_grid)

class InvFig(FigureCanvasQTAgg):
    def __init__(self, ui):
        fig_width, fig_height = 4, 4
        fig = mpl.figure.Figure(figsize=(fig_width, fig_height), facecolor= 'white')
        super(InvFig, self).__init__(fig)
        self.ui = ui
        self.initFig()

    def initFig(self):
        self.ax = self.figure.add_axes([0.05, 0.05, 0.9, 0.9])
        divider = make_axes_locatable(self.ax)
        divider.append_axes('right', size= 0.5, pad= 0.1)
        self.ax2 = self.figure.axes[1]
        self.ax.set_visible(False)
        self.ax2.set_visible(False)


    def plot_inv(self):

        self.ax.set_visible(True)
        self.ax2.set_visible(True)
        self.ax
        self.ax.cla()
        self.ax.set_title('LSQR')
        self.ax.set_xlabel('Distance [m]')
        self.ax.set_ylabel('Elevation [m]')

        slowness = self.ui.tomo.s
        grid = self.ui.models[self.ui.model_ind].grid
        noIter = self.ui.noIter
        cmax = max(np.abs(1/slowness))
        cmin = min(np.abs(1/slowness))
        mog = self.ui.models[self.ui.model_ind].mogs[0]
        color_limits_state = self.ui.set_color_checkbox.isChecked()
        cmap = self.ui.fig_combo.currentText()

        if color_limits_state:
            cmax = float(self.ui.Max_editi.text())
            cmin = float(self.ui.Min_editi.text())


        slowness = slowness.reshape((grid.grx.size -1, grid.grz.size-1)).T


        h = self.ax.imshow(np.abs(1/slowness), interpolation= 'none',cmap= cmap, vmax= cmax, vmin= cmin, extent= [grid.grx[0], grid.grx[-1], grid.grz[0], grid.grz[-1]])
        mpl.colorbar.Colorbar(self.ax2, h)

        for tick in self.ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(8)

        self.draw()

class RaysFig(FigureCanvasQTAgg):
    def __init__(self, ui):
        fig_width, fig_height = 6, 10
        fig = mpl.figure.Figure(figsize=(fig_width, fig_height),dpi= 80, facecolor='white')
        super(RaysFig, self).__init__(fig)
        self.ui = ui
        self.initFig()

    def initFig(self):
        self.ax = self.figure.add_axes([0.05, 0.05, 0.9, 0.9])
        divider = make_axes_locatable(self.ax)
        divider.append_axes('right', size= 0.5, pad= 0.1)
        self.ax2 = self.figure.axes[1]

    def plot_rays(self):
        self.ax.cla()
        for n in range(len(self.ui.tomo.rays)):
            h = self.ax.plot(self.ui.tomo.rays[n][:, 0], self.ui.tomo.rays[n][:, -1])
        mpl.colorbar.Colorbar(self.ax2, h)
        self.draw()

class RayDensityFig(FigureCanvasQTAgg):
    def __init__(self, ui):
        fig_width, fig_height = 6, 10
        fig = mpl.figure.Figure(figsize=(fig_width, fig_height),dpi= 80, facecolor='white')
        super(RayDensityFig, self).__init__(fig)
        self.ui = ui
        self.initFig()

    def initFig(self):
        self.ax = self.figure.add_axes([0.05, 0.05, 0.9, 0.9])
        divider = make_axes_locatable(self.ax)
        divider.append_axes('right', size= 0.5, pad= 0.1)
        self.ax2 = self.figure.axes[1]

    def plot_ray_density(self):
        #nCells = self.ui.tomo.L.shape[1]/2
        #Lx = self.ui.tomo.L[:, :nCells]
        #Lz = self.ui.tomo.L[:, 1+nCells:-1]

        dim = self.ui.models[self.ui.model_ind].grid.getNcell()
        grid = self.ui.models[self.ui.model_ind].grid

        #rd = np.full((1368,), sum(self.ui.tomo.L))
        tmp = sum(self.ui.tomo.L)
        rd = tmp.toarray()
        rd = rd.reshape((grid.grx.size -1, grid.grz.size-1)).T
        h = self.ax.imshow(rd, interpolation= 'none', cmap= 'inferno')
        mpl.colorbar.Colorbar(self.ax2, h)
        self.draw()

class ResidualsFig(FigureCanvasQTAgg):
    def __init__(self, ui):
        fig_width, fig_height = 10, 10
        fig = mpl.figure.Figure(figsize=(fig_width, fig_height),dpi= 80, facecolor='white')
        super(ResidualsFig, self).__init__(fig)
        self.ui = ui
        self.initFig()

    def initFig(self):
        self.ax1 = self.figure.add_axes([0.05, 0.55, 0.4, 0.4])
        self.ax2 = self.figure.add_axes([0.55, 0.55, 0.4, 0.4])
        self.ax3 = self.figure.add_axes([0.05, 0.05, 0.4, 0.4])
        self.ax4 = self.figure.add_axes([0.55, 0.05, 0.4, 0.4])
        divider = make_axes_locatable(self.ax4)
        divider.append_axes('right', size= 0.5, pad= 0.1)
        self.ax5 = self.figure.axes[4]

        #                      Layout
        # ---------------------------------------
        # |       ax1       |        ax2        |
        # ---------------------------------------
        # |       ax3       |      ax4/ax5      |
        # ---------------------------------------

        self.ax1.set_ylabel('||res||')
        self.ax1.set_xlabel('Iteration')

        self.ax2.set_ylabel('Residuals')
        self.ax2.set_xlabel('Angle with horizontal[°]')

        self.ax3.set_ylabel('Count')
        self.ax3.set_xlabel('Residuals')
        self.ax3.set_title('$\sigma^2$ = ')

        self.ax4.set_ylabel('Tx Depth')
        self.ax4.set_xlabel('Rx Depth')
        self.ax4.set_axis_bgcolor('grey')

    def plot_residuals(self):
        model = self.ui.models[self.ui.model_ind]
        data, idata = Model.getModelData(model, self.ui.air, self.ui.lsqrParams.selectedMogs, 'tt')
        data = np.concatenate((model.grid.Tx[idata, :], model.grid.Rx[idata, :], data), axis=1)

        hyp = np.sqrt(np.sum((data[:, 0:3]- data[:, 3:6])**2, axis=1))
        dz = data[:,2] - data[:,5]
        theta = 180/np.pi * np.arcsin(dz/hyp)

        nIt = self.ui.tomo.invData.res.shape[1]
        print(nIt)
        rms = np.zeros(nIt)

        for n in range(nIt):
            rms[n] = self.rmsv(self.ui.tomo.invData.res[n])

        res = self.ui.tomo.invData.res[:, nIt-1]
        vres = np.var(res)

        depth, i = Model.getModelData(model, self.ui.air, self.ui.lsqrParams.selectedMogs, 'tt', type2= 'depth')
        dTx = np.sort(np.unique(depth[:, 0]))
        print(dTx.shape)
        dRx = np.sort(np.unique(depth[:, 1]))
        print(dRx.shape)
        imdata = np.empty((len(dTx), len(dRx), ))
        imdata[:] = np.NAN

        #progressBar = QtGui.QProgressBar()
        #progressBar.setGeometry(200, 80, 250, 20)
        #progressBar.show()
        for i in range(len(dTx)):
            for j in range(len(dRx)):
                ind = np.logical_and(dTx[i] == depth[:, 0], dRx[j] == depth[:, 1])
                if sum(ind.astype(int)) == 1:
                    imdata[i, j] = res[ind]


                #progressBar.setValue(i/len(dTx))



        self.ax1.plot(np.arange(nIt), rms[:nIt], marker = 'o', ls= 'none')
        self.ax1.set_xlim(-0.3, nIt - 0.7)
        self.ax1.set_ylim(min(rms) - 0.3, max(rms) + 0.3)
        self.ax1.set_xticks(np.arange(nIt))

        self.ax2.plot(theta, res, marker= 'o', ls= 'none')

        self.ax3.hist(res)
        self.ax3.set_title('$\sigma^2$ = {}'.format(vres))

        h = self.ax4.imshow(imdata, aspect= 'auto', interpolation= 'none', cmap= 'seismic')

        mpl.colorbar.Colorbar(self.ax5, h)

        self.draw()

    def rmsv(self, x):
        x = x.flatten()
        r = np.sqrt(sum(x**2)/len(x))
        return r


class TomoFig(FigureCanvasQTAgg):
    def __init__(self, ui):
        fig_width, fig_height = 6, 10
        fig = mpl.figure.Figure(figsize=(fig_width, fig_height),dpi= 80, facecolor='white')
        super(TomoFig, self).__init__(fig)
        self.ui = ui
        self.initFig()

    def initFig(self):
        self.ax = self.figure.add_axes([0.05, 0.05, 0.9, 0.9])
        divider = make_axes_locatable(self.ax)
        divider.append_axes('right', size= 0.5, pad= 0.1)
        self.ax2 = self.figure.axes[1]
        self.ax2.set_title('m/ns')

    def plot_tomo(self):
        grid = self.ui.models[self.ui.model_ind].grid
        s = self.ui.tomo.s

        cmax = max(1/s)
        cmin = min(1/s)

        s = s.reshape((grid.grx.size -1, grid.grz.size-1)).T

        h = self.ax.imshow(1/s, interpolation= 'none', cmap= 'inferno', vmax= cmax, vmin= cmin, extent= [grid.grx[0], grid.grx[-1], grid.grz[0], grid.grz[-1]])
        mpl.colorbar.Colorbar(self.ax2, h)

        for tick in self.ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(8)



        self.draw()




class InvLSQRParams:
    def __init__(self):
        self.tomoAtt        = 0
        self.selectedMogs   = []
        self.numItStraight  = 0
        self.numItCurved    = 0
        self.saveInvData    = 1
        self.useCont        = 0
        self.tol            = 0
        self.wCont          = 0
        self.alphax         = 0
        self.alphay         = 0
        self.alphaz         = 0
        self.order          = 1
        self.nbreiter       = 0
        self.dv_max         = 0

class Tomo:
    def __init__(self):
        self.rays   = np.array([])
        self.L      = np.array([])
        self.invData = invData()
        self.no_trace = np.array([])
        self.x = np.array([])
        self.y = np.array([])
        self.z = np.array([])
        self.s = 0
        self.res = np.array([0])
        self.var_res = np.array([])

class invData:
    def __init__(self):
        self.res = np.array([0])
        self.s = np.array([0])



#--- Class For Alignment ---#
class  MyQLabel(QtGui.QLabel):
    def __init__(self, label, ha='left',  parent=None):
        super(MyQLabel, self).__init__(label,parent)
        if ha == 'center':
            self.setAlignment(QtCore.Qt.AlignCenter)
        elif ha == 'right':
            self.setAlignment(QtCore.Qt.AlignRight)
        else:
            self.setAlignment(QtCore.Qt.AlignLeft)

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)

    inv_ui = InversionUI()
#    inv_ui.openmain.load_file('C:\\Users\\Utilisateur\\PycharmProjects\\BhTomoPy\\test_constraints.p')
    inv_ui.openmain.load_file('test_constraints.p')
    inv_ui.openmain.ok()
    inv_ui.showMaximized()
    #residuals = ResidualsFig(inv_ui)
    #residuals.showMaximized()

    sys.exit(app.exec_())
