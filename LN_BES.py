#!/usr/bin/env python
# -*- coding: utf-8 -*-
#Created by Max T. Curie 09/07/2020
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ParIO import Parameters 
from LN_tools import get_suffix
from LN_tools import start_end_time
from LN_tools import BES_f_spectrum_sum_then_FFT

#*****************************************************************
#*******************Beginning of the User block*******************

Delta_Z=0.02  #7cm as bin for Z 

time_step=1     #read time with this step size
frequency_all=False      #Switch to True if one wants to sum over all fequency 

frequency_max=-249.5       #maximum frequency(Lab Frame) to sum over in kHz
frequency_min=-250.5       #minimum frequency(Lab Frame) in sum over in kHz

pic_path='BES_pic'        #path one want to store the picture and video in
csv_path='BES_csv'        #path one want to store the picture and video in
iterdb_file_name='/global/u1/m/maxcurie/max/Cases/DIIID175823_250k/DIIID175823.iterdb'
manual_Doppler=-7.	#if it is number, then manually put in the doppler shift in kHz for n=1, Type False if one to calculate the Doppler shift from ITERDB

#*********************End of the User block***********************
#*****************************************************************

max_Z0=Delta_Z/2.   
min_Z0=-Delta_Z/2.

Outboard_mid_plane=False  #change to True if one wants to only want to look at outboard mid-plane
plot=False
show=False
csv_output=False

suffix=get_suffix()
par = Parameters()
par.Read_Pars('parameters'+suffix)
pars = par.pardict
time_start,time_end=start_end_time(suffix,pars)

f,n1_f=\
        BES_f_spectrum_sum_then_FFT(suffix,iterdb_file_name,manual_Doppler,\
        	min_Z0,max_Z0,Outboard_mid_plane,\
        	time_step,time_start,time_end,\
            plot,show,csv_output,pic_path,csv_path)
len_f=len(f)

n1_BES0=0.

for i_f in range(len_f):
    if frequency_min<=f[i_f] and f[i_f]<=frequency_max:
        n1_BES0=n1_BES0+abs(n1_f[i_f])

nref = pars['nref']         #in 10^(19) /m^3
n1_BES=n1_BES0

file=open("0BES.txt","w")
file.write('n1_BES='+str(n1_BES)+'/m^3\n')
print('n1_BES='+str(n1_BES)+'/m^3')
file.write('n0='+str(nref)+'*10^19/m^3')
print('n0='+str(nref)+'*10^19/m^3')

