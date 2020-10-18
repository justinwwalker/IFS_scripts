import matplotlib.pyplot as plt
import numpy as np
import csv
import os

from genetools import *
from max_mode_judge import D_chi_3
from max_mode_judge import D_chi_3_judge

#Last edited by Max Curie 10/16/2020

#************Start of User block*********************
scan_name='nu_ei'  #name of scanning quantity
spec_num=3 #number of the specices 1 or 3

#************End of User block*********************


def get_omega(suffix):
    evals = np.genfromtxt('eigenvalues_'+suffix) 
    
    #print(evals)
    gamma_list = []
    omega_list = []
   
    for line in evals:
        omega_list.append(line[1])
        gamma_list.append(line[0])

    indice_list = np.arange(len(omega_list))

    return gamma_list,omega_list,indice_list


def D_chi_e(suffix,index0):

    #from genetools.py
    paramfpath="parameters_"+str(suffix)
    geneparam=read_parameters(paramfpath)

    Tref=geneparam['units']['Tref']
    nref=geneparam['units']['nref']

    species=['e']
    Te=geneparam['species1']['temp']
    ne=geneparam['species1']['dens']
    omn_e=geneparam['species1']['omn']
    omt_e=geneparam['species1']['omt']
    
    #from genetools.py
    nrgfpath="nrg_"+str(suffix)
    nrgdata = read_nrg(nrgfpath)

    D_e=nrgdata[nrgfpath]['e']['PFluxes'][index0]+nrgdata[nrgfpath]['e']['PFluxem'][index0]
    D_e=D_e/ omn_e / ne
    Qes_e=nrgdata[nrgfpath]['e']['HFluxes'][index0]-3./2.*Te*nrgdata[nrgfpath]['e']['PFluxes'][index0]
    Qem_e=nrgdata[nrgfpath]['e']['HFluxem'][index0]-3./2.*Te*nrgdata[nrgfpath]['e']['PFluxem'][index0]
    Q_e = (Qes_e+Qem_e)
    chi_e = (Qes_e+Qem_e) / omt_e / ne / Te

    return Qes_e,Qem_e,Q_e,D_e,chi_e

def D_chi_e_judge(Qes_e,Qem_e,Q_e,D_e,chi_e):

    if abs(Qem_e/Qes_e) >= 1 and abs(D_e/chi_e)<0.6:
        mode="MTM"
    elif abs(Qem_e/Qes_e) >= 1 and abs(D_e/chi_e)>0.6:
        mode="KBM"
    elif abs(Qem_e/Qes_e) < 1 and abs(D_e/chi_e)<0.6:
        mode="ETG"
    else:
        mode="other"
    return mode



def scan_cases_e():
    csvfile_name='EV_log.csv'
    with open(csvfile_name, 'w', newline='') as csvfile:
        data = csv.writer(csvfile, delimiter=',')
        data.writerow(['Suffix','index',scan_name,'omega','gamma','mode','Qem_e/Qes_e','D_e/chi_e'])
        csvfile.close()

    cwd = os.getcwd()
    filelist = []
    for filename in os.listdir(cwd):
        if filename.startswith("field"):
            filelist.append(filename[-4:])
    filelist.sort()
    for suffix in filelist:
        print('*************reading'+suffix+'*************')
        gamma_list,omega_list,indice_list=get_omega(suffix)
        for index0 in indice_list:
            print('****'+str(index0)+'*****')
            Qes_e,Qem_e,Q_e,D_e,chi_e=D_chi_e(suffix,index0)
            mode=D_chi_3_judge(Qes_e,Qes_i,Qes_z,Qem_e,Qem_i,Qem_z,Q_e,Q_i,Q_z,D_e,D_i,D_z,chi_e,chi_i,chi_z)
            print('****'+str(mode)+'*****')
            
            par = Parameters()
            par.Read_Pars('parameters_'+suffix)
            pars = par.pardict
            scan_quant=pars[scan_name]

            with open(csvfile_name, 'a+', newline='') as csvfile:
                data = csv.writer(csvfile, delimiter=',')
                data.writerow([suffix,index0,scan_quant,omega_list[index0],gamma_list[index0],mode,Qem_e/Qes_e,D_e/chi_e,])
                csvfile.close()

def scan_cases_3():
    csvfile_name='EV_log.csv'
    with open(csvfile_name, 'w', newline='') as csvfile:
        data = csv.writer(csvfile, delimiter=',')
        data.writerow(['Suffix','index',scan_name,'omega','gamma','mode','Qem_e/Qes_e','D_e/chi_e','chi_i/chi_e','Q_i/Q_e','D_e/chi_tot'])
        csvfile.close()

    cwd = os.getcwd()
    filelist = []
    for filename in os.listdir(cwd):
        if filename.startswith("field"):
            filelist.append(filename[-4:])
    filelist.sort()
    for suffix in filelist:
        print('*************reading'+suffix+'*************')
        gamma_list,omega_list,indice_list=get_omega(suffix)
        for index0 in indice_list:
            print('****'+str(index0)+'*****')
            Qes_e,Qes_i,Qes_z,Qem_e,Qem_i,Qem_z,Q_e,Q_i,Q_z,D_e,D_i,D_z,chi_e,chi_i,chi_z=D_chi_3(suffix,index0)
            mode=D_chi_3_judge(Qes_e,Qes_i,Qes_z,Qem_e,Qem_i,Qem_z,Q_e,Q_i,Q_z,D_e,D_i,D_z,chi_e,chi_i,chi_z)
            print('****'+str(mode)+'*****')
            
            par = Parameters()
            par.Read_Pars('parameters_'+suffix)
            pars = par.pardict
            scan_quant=pars[scan_name]

            with open(csvfile_name, 'a+', newline='') as csvfile:
                data = csv.writer(csvfile, delimiter=',')
                data.writerow([suffix,index0,scan_quant,omega_list[index0],gamma_list[index0],mode,Qem_e/Qes_e,D_e/chi_e,chi_i/chi_e,Q_i/Q_e,D_e/(chi_e+chi_i+chi_z)])
                csvfile.close()
    

if spec_num==1:
    scan_cases_e()
elif spec_num==3:
    scan_cases_3()