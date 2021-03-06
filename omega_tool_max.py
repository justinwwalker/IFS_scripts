#!/usr/bin/env python
# -*- coding: utf-8 -*-

import optparse as op
import math
import cmath
import sys
import numpy as np
import matplotlib.pyplot as plt
from fieldsWrapper import *
from parIOWrapper import init_read_parameters_file
from finite_differences import *
from fieldlib import *
from max_stat_tool import *

#Rescale test path: /global/cscratch1/sd/maxcurie/local_scan/ky_scan/rescale_test
#shortcut name: omega_max
#shortcut for test: omega_test
def omega_calc(suffix):
    percent=20#percentage of the time to calculate the omega
#    parser = op.OptionParser(description='')
#    parser.add_option('--show_plots','-p',action='store',dest='show_plots',help = 'Display the variation as a function of z',default=False)
    pars = init_read_parameters_file(suffix)
#    options = parser.parse_args()
#    show_plots = options.show_plots
    field = fieldfile('field'+suffix,pars)
    tend = field.tfld[-1]
    tstart = field.tfld[-1]*(100-percent)/100
    #tstart = field.tfld[0]
    #print tend, tstart
    imax = np.unravel_index(np.argmax(abs(field.phi()[:,0,:])),(field.nz,field.nx))
    phi_t = []

    time = np.empty(0)
    #print np.array(field.tfld)
    istart = np.argmin(abs(np.array(field.tfld)-tstart))
    iend = np.argmin(abs(np.array(field.tfld)-tend))
    phi = np.empty(0,dtype='complex128')
    for i in range(istart,iend):
        field.set_time(field.tfld[i])
        phi, apar = eigenfunctions_from_field_file(pars,suffix,False,False,field.tfld[i],False,False)  
        #print i 
        #print phi[1]
        phi_t.append(phi)
        time = np.append(time,field.tfld[i])
    phi_t = np.array(phi_t)
    omega_t = []
    omega_avg = np.empty(0,dtype='complex128')
    #print phi_t
    if len(phi_t)<1:
        omega_output=0
        gamma_output=0
        f=open('omega'+suffix,'w')
        f.write(str(pars['kymin'])+'    '+str(gamma_output)+'    '+str(omega_output)+'\n')
        f.close()
        print("Error, Field file is empty")
        return gamma_output, omega_output
        end()
    else: 
        zmax = len(phi_t[1])
        #print len(field.tfld)
        #print np.shape(phi_t)
        #print 'zmax', zmax
        #print istart
        #print iend
        omega_list=[]
        gamma_list=[]
        i=0
        f=open('omega_test'+suffix,'w')
        
        for t in range(1,iend-istart):
            delta_t = field.tfld[t]-field.tfld[t-1]
            avg_temp=0
            for z in range(zmax):
                #temp=z
                #z=t
                #t=temp
                if phi_t[t-1,z] ==0: continue
                if abs(phi_t[t,z]/phi_t[t-1,z])==0: 
                    omega_t.append(0)
                elif (phi_t[t,z]/phi_t[t-1,z]).imag ==0 and (phi_t[t,z]/phi_t[t-1,z]).imag < 0:
                    omega_t.append(complex(0,np.pi)*cmath.log(abs(phi_t[t,z]/phi_t[t-1,z]))/(field.tfld[t]-field.tfld[t-1]))
                else:
                    omega_t.append(cmath.log((phi_t[t,z]/phi_t[t-1,z]))/(field.tfld[t]-field.tfld[t-1]))
                #print t , z
                #print omega_t[i]
                f.write('t='+str(t*delta_t)+'s     '+str(omega_t[i])+'\n')
                avg_temp=avg_temp+omega_t[i]
                i=i+1
            #print t
            avg_temp=avg_temp/zmax
            omega_list.append(avg_temp.imag)
            gamma_list.append(avg_temp.real)
            #print(omega_t)
        f.close()

        omega_output=avg(omega_list,3)
        gamma_output=avg(gamma_list,3)
        f=open('omega'+suffix,'w')
        f.write(str(pars['kymin'])+'    '+str(gamma_output[0])+'    '+str(omega_output[0])+'\n')
        f.close()
        
        print((" gamma is: ", gamma_output[0], "gamma_dev is", gamma_output[1]))
        print(("omega is: ", omega_output[0], "omega_dev is", omega_output[1]))
        
        return gamma_output, omega_output
