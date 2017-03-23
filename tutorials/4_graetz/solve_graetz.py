# Copyright (C) 2015-2016 SISSA mathLab
#
# This file is part of RBniCS.
#
# RBniCS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RBniCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with RBniCS. If not, see <http://www.gnu.org/licenses/>.
#
## @file solve_graetz.py
#  @brief Example 4: Graetz test case
#
#  @author Francesco Ballarin <francesco.ballarin@sissa.it>
#  @author Gianluigi Rozza    <gianluigi.rozza@sissa.it>
#  @author Alberto   Sartori  <alberto.sartori@sissa.it>

from dolfin import *
from RBniCS import *

#~~~~~~~~~~~~~~~~~~~~~~~~~     EXAMPLE 4: GRAETZ CLASS     ~~~~~~~~~~~~~~~~~~~~~~~~~#
class Graetz(ShapeParametrization(EllipticCoerciveRBNonCompliantBase)):

    ###########################     CONSTRUCTORS     ###########################
    ## @defgroup Constructors Methods related to the construction of the reduced order model object
    #  @{

    ## Default initialization of members
    def __init__(self, V, mesh, subd, bound):
        # Store the BC object for the homogeneous solution (after lifting)
        bc_list = [
            DirichletBC(V, 0.0, bound, 1), # indeed homog. bcs
            DirichletBC(V, 0.0, bound, 5), # indeed homog. bcs
            DirichletBC(V, 0.0, bound, 6) # indeed homog. bcs
            #DirichletBC(V, 0.0, bound, 2), # non-homog. bcs with a lifting
            #DirichletBC(V, 0.0, bound, 4)  # non-homog. bcs with a lifting
        ]
        # Declare the shape parametrization map
        shape_parametrization_expression = [
            ("x[0]", "x[1]"), # subdomain 1
            ("mu[0]*(x[0] - 1) + 1", "x[1]"), # subdomain 2
        ]
        # Call the standard initialization
        super(Graetz, self).__init__(mesh, subd, V, bc_list, shape_parametrization_expression)
        # ... and also store FEniCS data structures for assembly
        self.dx = Measure("dx")(subdomain_data=subd)
        self.ds = Measure("ds")(subdomain_data=bound)

        # Store the velocity expression
        self.vel = Expression("x[1]*(1-x[1])", degree=self.V.ufl_element().degree())
        # Finally, initialize an SCM object to approximate alpha LB
        self.SCM_obj = SCM_Graetz(self)

    #  @}
    ########################### end - CONSTRUCTORS - end ###########################

    ###########################     SETTERS     ###########################
    ## @defgroup Setters Set properties of the reduced order approximation
    #  @{

    # Propagate the values of all setters also to the SCM object

    def setNmax(self, nmax):
        EllipticCoerciveRBNonCompliantBase.setNmax(self, nmax)
        self.SCM_obj.setNmax(2*nmax)
    def settol(self, tol):
        EllipticCoerciveRBNonCompliantBase.settol(self, tol)
        self.SCM_obj.settol(tol)
    def setmu_range(self, mu_range):
        EllipticCoerciveRBNonCompliantBase.setmu_range(self, mu_range)
        self.SCM_obj.setmu_range(mu_range)
    def setxi_train(self, ntrain, enable_import=False, sampling="random"):
        EllipticCoerciveRBNonCompliantBase.setxi_train(self, ntrain, enable_import, sampling)
        self.SCM_obj.setxi_train(ntrain, True, sampling)
    def setxi_test(self, ntest, enable_import=False, sampling="random"):
        EllipticCoerciveRBNonCompliantBase.setxi_test(self, ntest, enable_import, sampling)
        self.SCM_obj.setxi_test(ntest, True, sampling)
    def setmu(self, mu):
        EllipticCoerciveRBNonCompliantBase.setmu(self, mu)
        self.SCM_obj.setmu(mu)

    #  @}
    ########################### end - SETTERS - end ###########################

    ###########################     PROBLEM SPECIFIC     ###########################
    ## @defgroup ProblemSpecific Problem specific methods
    #  @{

    ## Return the alpha_lower bound.
    def get_alpha_lb(self):
        return self.SCM_obj.get_alpha_LB(self.mu)

    ## Set theta multiplicative terms of the affine expansion of a.
    def compute_theta_a(self):
        mu1 = self.mu[0]
        mu2 = self.mu[1]
        theta_a0 = mu2
        theta_a1 = mu2/mu1
        theta_a2 = mu1*mu2
        theta_a3 = 1.0
        return (theta_a0, theta_a1, theta_a2, theta_a3)

    ## Set theta multiplicative terms of the affine expansion of f.
    def compute_theta_f(self):
        mu1 = self.mu[0]
        mu2 = self.mu[1]
        mu3 = self.mu[2]
        theta_f0 = - mu3
        # theta_f0 = - mu2
        # theta_f1 = - mu2/mu1
        # theta_f2 = - mu1*mu2
        # theta_f3 = - 1.0
        return (theta_f0,)

    ## Set theta multiplicative terms of the affine expansion of s.
    def compute_theta_s(self):
        return (1.0,)

    ## Set matrices resulting from the truth discretization of a.
    def assemble_truth_a(self):
        u = self.u
        v = self.v
        dx = self.dx
        vel = self.vel
        # Define
        a0 = inner(grad(u),grad(v))*dx(1) + 1e-15*u*v*dx
        a1 = u.dx(0)*v.dx(0)*dx(2) + 1e-15*u*v*dx
        a2 = u.dx(1)*v.dx(1)*dx(2) + 1e-15*u*v*dx
        a3 = vel*u.dx(0)*v*dx(1) + vel*u.dx(0)*v*dx(2) + 1e-15*u*v*dx
        # Assemble
        A0 = assemble(a0)
        A1 = assemble(a1)
        A2 = assemble(a2)
        A3 = assemble(a3)
        # Return
        return (A0, A1, A2, A3)

    ## Set vectors resulting from the truth discretization of f.
    def assemble_truth_f(self):
        v = self.v
        ds = self.ds
        vel = self.vel
        #lifting = self.lifting
        # Define
        f0 = v * ds(2) + v * ds(4)
        #f0 = inner(grad(lifting),grad(v))*dx(1) + 1e-15*lifting*v*dx
        #f1 = lifting.dx(0)*v.dx(0)*dx(2) + 1e-15*lifting*v*dx
        #f2 = lifting.dx(1)*v.dx(1)*dx(2) + 1e-15*lifting*v*dx
        #f3 = vel*lifting.dx(0)*v*dx(1) + vel*lifting.dx(0)*v*dx(2) + 1e-15*lifting*v*dx
        # Assemble
        F0 = assemble(f0)
        # F0 = assemble(f0)
        # F1 = assemble(f1)
        # F2 = assemble(f2)
        # F3 = assemble(f3)
        # Return
        return (F0,)

    ## Set vectors resulting from the truth discretization of s.
    def assemble_truth_s(self):
        v = self.v
#        ds = self.ds
#        s0 = v*ds(3)
        dx = self.dx
        s0 = v*dx(2)

        # Assemble and return
        S0 = assemble(s0)
        return (S0,)

    #  @}
    ########################### end - PROBLEM SPECIFIC - end ###########################

    ###########################     OFFLINE STAGE     ###########################
    ## @defgroup OfflineStage Methods related to the offline stage
    #  @{

    ## Perform the offline phase of the reduced order model
    def offline(self):
        # Perform first the SCM offline phase, ...
        bak_first_mu = tuple(list(self.mu))
        self.SCM_obj.offline()
        # ..., and then call the parent method.
        self.setmu(bak_first_mu)
        EllipticCoerciveRBNonCompliantBase.offline(self)

    #  @}
    ########################### end - OFFLINE STAGE - end ###########################

    ###########################     I/O     ###########################
    ## @defgroup IO Input/output methods
    #  @{

    ## Preprocess the solution before plotting to add a lifting
    def preprocess_solution_for_plot(self, solution):
        #solution_with_lifting = Function(self.V)
        #solution_with_lifting.vector()[:] = solution.vector()[:] + self.lifting.vector()[:]
        return solution

    #  @}
    ########################### end - I/O - end ###########################

    ###########################     ERROR ANALYSIS     ###########################
    ## @defgroup ErrorAnalysis Error analysis
    #  @{

    # Compute the error of the reduced order approximation with respect to the full order one
    # over the test set
    def error_analysis(self, N=None):
        # Perform first the SCM error analysis, ...
        self.SCM_obj.error_analysis()
        # ..., and then call the parent method.
        EllipticCoerciveRBNonCompliantBase.error_analysis(self, N)

    #  @}
    ########################### end - ERROR ANALYSIS - end ###########################

#~~~~~~~~~~~~~~~~~~~~~~~~~     EXAMPLE 4: SCM CLASS     ~~~~~~~~~~~~~~~~~~~~~~~~~#
class SCM_Graetz(SCM):

    ###########################     CONSTRUCTORS     ###########################
    ## @defgroup Constructors Methods related to the construction of the reduced order model object
    #  @{

    ## Default initialization of members
    def __init__(self, parametrized_problem):
        # Call the standard initialization
        SCM.__init__(self, parametrized_problem)

        # Good guesses to help convergence of bounding box
        self.guess_bounding_box_minimum = (1.e-5, 1.e-5, 1.e-5, 1.e-5)
        self.guess_bounding_box_maximum = (1., 1., 1., 1.)

    #  @}
    ########################### end - CONSTRUCTORS - end ###########################

    ###########################     PROBLEM SPECIFIC     ###########################
    ## @defgroup ProblemSpecific Problem specific methods
    #  @{

    ## Set additional options for the eigensolver (bounding box minimum)
    def set_additional_eigensolver_options_for_bounding_box_minimum(self, eigensolver, qa):
        eigensolver.parameters["spectral_transform"] = "shift-and-invert"
        eigensolver.parameters["spectral_shift"] = self.guess_bounding_box_minimum[qa]

    ## Set additional options for the eigensolver (bounding box maximimum)
    def set_additional_eigensolver_options_for_bounding_box_maximum(self, eigensolver, qa):
        eigensolver.parameters["spectral_transform"] = "shift-and-invert"
        eigensolver.parameters["spectral_shift"] = self.guess_bounding_box_maximum[qa]

    #  @}
    ########################### end - PROBLEM SPECIFIC - end ###########################


#~~~~~~~~~~~~~~~~~~~~~~~~~     EXAMPLE 4: MAIN PROGRAM     ~~~~~~~~~~~~~~~~~~~~~~~~~#

# 1. Read the mesh for this problem
mesh = Mesh("data/graetz.xml")
subd = MeshFunction("size_t", mesh, "data/graetz_physical_region.xml")
bound = MeshFunction("size_t", mesh, "data/graetz_facet_region.xml")

# 2. Create Finite Element space (Lagrange P1)
V = FunctionSpace(mesh, "Lagrange", 1)

# 3. Allocate an object of the Graetz class
graetz = Graetz(V, mesh, subd, bound)

# 4. Choose PETSc solvers as linear algebra backend
parameters.linear_algebra_backend = 'PETSc'

# 5. Set mu range, xi_train and Nmax
mu_range = [(0.01, 10.0), (0.01, 10.0), (-1.0,1.0)]
graetz.setmu_range(mu_range)
graetz.setxi_train(100)
graetz.setNmax(10)

# 6. Perform the offline phase
first_mu = (1.0, 1.0, 0.30)
graetz.setmu(first_mu)
graetz.offline()

# 7. Perform an online solve
online_mu = (10.0, 0.01, 0.30)
graetz.setmu(online_mu)
graetz.online_solve()
