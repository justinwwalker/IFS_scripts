import os
import sys
import numpy as np
import optparse as op
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.pyplot as plt
import imageio   #for making animation

from nrgWrapper import read_from_nrg_files
from parIOWrapper import read_species_gradients
from parIOWrapper import read_species_tempdens
from ParIO import Parameters 
from fieldlib import fieldfile
from geomWrapper import ky
from geomWrapper import init_read_geometry_file
from read_write_geometry import read_geometry_local
from read_iterdb_file import read_iterdb_file
from interp import interp
from FFT_general import FFT_function_time
from max_stat_tool import sort_x_f


#input the suffix , plot nrg_es, em, return time_start,time_end
#from LN_tools import start_end_time
#time_start,time_end=start_end_time(suffix,pars)
def get_suffix():
    parser=op.OptionParser(description='Some infrastructure for reading in, manipulating, and plotting nonlinear field data.')
    #parser.add_option('--plot_theta','-g',action='store_const',const=False,help = 'Plot global mode structures decomposed in poloidal m number.',default=True)
    options,args=parser.parse_args()
    print("options",options)
    print("args",args)
    if len(args)!=1:
        exit("""
    Please include run number as argument (e.g., 0001)."
        \n""")
    suffix = args[0]
    
    if suffix in ['dat','.dat']:
        suffix = '.dat'
    else:
        suffix = '_'+suffix
    return suffix

def start_end_time(suffix,pars):  #suffix in the format of "_1" or ".dat"


    if pars['n_spec'] == 1:
        time, nrge = read_from_nrg_files(pars,suffix,False)
    elif pars['n_spec'] == 2:
        time, nrgi, nrge = read_from_nrg_files(pars,suffix,False)
    elif pars['n_spec'] == 3:
        time, nrgi, nrge, nrgz = read_from_nrg_files(pars,suffix,False)

    plt.clf()
    plt.plot(time,nrge[:,6],label="Q_es of electron")
    plt.plot(time,nrge[:,7],label="Q_em of electron")
    plt.title('nrg of electron')
    plt.xlabel('time')
    plt.legend()
    plt.show()
    
    scan_all = str(input("Scan all(Y/N):\n"))
    if scan_all=='n' or scan_all=='N':
        time_start = float(input("Start time:\n"))
        time_end = float(input("End time:\n"))
        time_start_index=np.argmin(abs(time-float(time_start)))
        time_end_index=np.argmin(abs(time-float(time_end)))
        time_start = time[time_start_index]
        time_end = time[time_end_index]
    elif scan_all=='y' or scan_all=='Y':
        time_start = time[0]
        time_end = time[-1]
        time_start_index=0
        time_end_index=len(time)-1
    else:
        print("Please respond with y, Y , n, N")
        sys.exit()

    plt.clf()
    plt.plot(time,nrge[:,6],label="Q_es of electron")
    plt.plot(time,nrge[:,7],label="Q_em of electron")
    plt.title('nrg of electron')
    plt.axvline(time_start,color='red',label="time start",alpha=1)
    plt.axvline(time_end,color='blue',label="time end",alpha=1)
    plt.xlabel('time')
    plt.legend()
    plt.show()

    return time_start,time_end

# n_list, ky_list=ky_list_calc(suffix)
def ky_list_calc(suffix):
    #Import the parameters from parameter file using ParIO
    par = Parameters()
    par.Read_Pars('parameters'+suffix)
    pars = par.pardict

    B_gauss=10.**4              #1T=10^4Gauss
    qref = 1.6E-19              #in C
    c  = 1.                     #in 3*10^8m/s
    m_kg = 1.673E-27            #in kg
    Bref = pars['Bref']         #in Tesla
    Tref = pars['Tref']         #in keV
    nref = pars['nref']         #in 10^(19) /m^3
    Lref = pars['Lref']         #in m
    mref = pars['mref']         #in proton mass(kg)
    q0 = pars['q0']              #unitless, safety factor/q95
    x0 = pars['x0']             #x/a, location
    kymin = pars['kymin']       #in rhoi
    nky0 = pars['nky0']         #in total number of ky
    n_step = pars['n0_global']  #in rhoi
    nref = nref * 1.E19         #in the unit of /m^3
    Tref = Tref * qref * 1.E03  #in the unit of J
    mref = mref * m_kg          #in the unit of kg
    pref = nref * Tref          #in Pa*k_{B}
    cref = np.sqrt(Tref / mref) #in the unit of m/s
    Omegaref = qref * Bref / mref / c  #in rad/s
    rhoref = cref / Omegaref           #in m rho_i(ion gyroradii)
    rhorefStar = rhoref / Lref         #Unitless
    gyroFreq= cref/Lref                 #the facor convert frequency from cs/a to rad/s


    #Determine the n for kymin
    ky_n1=1.*q0*rhoref/(Lref*x0)  #ky for n=1
    n_min=round(kymin/ky_n1)   #n for ky_min
    if n_min==0:
        n_min=1
    n_list=np.arange(int(n_min),int(n_min+nky0*n_step),int(n_step))
    ky_list=ky_n1*n_list
    return n_list, ky_list
#input the suffix and nz index, time_start and end, return the Br as function of frequency(frequency_kHZ,amplitude_frequency_sum,amplitude_growth_sum)
#from LN_tools import LN_apar_frequency_nz
#For report == False
#frequency_kHZ,amplitude_frequency_sum,amplitude_growth_sum=LN_apar_frequency(suffix,inz,time_start,time_end,plot=False,pic_path='pic',csv_path='csv',output_csv=False,show=False)
#For report == True
#frequency_kHZ,amplitude_frequency_sum,amplitude_growth_sum=LN_apar_frequency_nz(suffix,inz,time_start,time_end,plot=True,pic_path='pic/nz_',csv_path='csv/nz_'+str(inz),output_csv=True,show=False)
def LN_apar_frequency_nz(suffix,inz,time_start,time_end,plot=False,pic_path='pic',csv_path='csv',output_csv=False,show=False):
    #Where inz is the number of the element in nz

    #Import the parameters from parameter file using ParIO
    par = Parameters()
    par.Read_Pars('parameters'+suffix)
    pars = par.pardict
    #getting B field using read_write_geometry.py
    gpars,geometry = read_geometry_local(pars['magn_geometry'][1:-1]+suffix)
    #Get geom_coeff from ParIO Wrapper
    geom_type, geom_pars, geom_coeff = init_read_geometry_file(suffix, pars)
    #Import the field file using fieldlib
    field = fieldfile('field'+suffix,pars)
    time = np.array(field.tfld)  #time stampes

    B_gauss=10.**4              #1T=10^4Gauss
    qref = 1.6E-19              #in C
    c  = 1.                     #in 3*10^8m/s
    m_kg = 1.673E-27            #in kg
    Bref = pars['Bref']         #in Tesla
    Tref = pars['Tref']         #in keV
    nref = pars['nref']         #in 10^(19) /m^3
    Lref = pars['Lref']         #in m
    mref = pars['mref']         #in proton mass(kg)
    q0 = pars['q0']              #unitless, safety factor/q95
    x0 = pars['x0']             #x/a, location
    kymin = pars['kymin']       #in rhoi
    nky0 = pars['nky0']         #in total number of ky
    n_step = pars['n0_global']  #in rhoi
    nref = nref * 1.E19         #in the unit of /m^3
    Tref = Tref * qref * 1.E03  #in the unit of J
    mref = mref * m_kg          #in the unit of kg
    pref = nref * Tref          #in Pa*k_{B}
    cref = np.sqrt(Tref / mref) #in the unit of m/s
    Omegaref = qref * Bref / mref / c  #in rad/s
    rhoref = cref / Omegaref           #in m rho_i(ion gyroradii)
    rhorefStar = rhoref / Lref         #Unitless
    gyroFreq= cref/Lref                 #the facor convert frequency from cs/a to rad/s


    #ky comes from geomWrapper.py
    ky_GENE_temp=ky(pars, geom_coeff,plot=False)     #ky for ky min for differen z
    #print('ky shape: '+str(np.shape(ky_GENE_temp)))

    #Determine the n for kymin
    ky_n1=1.*q0*rhoref/(Lref*x0)  #ky for n=1
    n_min=round(kymin/ky_n1)   #n for ky_min
    if n_min==0:
        n_min=1
    n_list=np.arange(int(n_min),int(n_min+nky0*n_step),int(n_step))

    ky_GENE_n1=ky_GENE_temp/float(n_min)
    ky_GENE_grid = np.outer(ky_GENE_n1,n_list) #outer product of the two vectors
    
    print("kygrid"+str(np.shape(ky_GENE_grid)))
    
    print('n0 list length: '+str(len(n_list)))
    print('n0 list: '+str(n_list))
    
    
    #B1=abs(np.mean(Apar_GENE[z,:])*len(Apar_GENE[z,:])*(ky_GENE_temp[z]/rhoref)*Bref*B_gauss*rhorefStar*rhoref)
    Apar_to_B1=abs((1./rhoref)*Bref*B_gauss*rhorefStar*rhoref)         #B1=Apar*ky_GENE_temp*Apar_to_B1

    
    time_start_index=np.argmin(abs(time - time_start))
    time_end_index=np.argmin(abs(time - time_end))
    time_list = time[time_start_index:time_end_index+1]
    
    nky0=len(n_list)
    ntime=len(time_list)
    B1_ky_t_inz=np.zeros((nky0,ntime))

    if os.path.isdir(csv_path):  #if path does not exist, then create 'csv'
        pass
    else:
        os.mkdir(csv_path) 
    if os.path.isdir(pic_path):  #if path does not exist, then create 'pic'
        pass
    else:
        os.mkdir(pic_path) 
    print("**********Scan starts, output in csv and pic***************")


    for i in range(len(time_list)):
        time0=time_list[i]
        itime = np.argmin(abs(time - time0))
        
        print("Looking at the spectra at time:"+str(time[itime]))
        #This sets the time step you want to read in
        field.set_time(time[itime])
        
        
        if 'x_local' in pars:
            if pars['x_local']:
                x_local = True
            else:
                x_local = False 
        else:
            x_local = True

        if x_local:
            kxmin = 2.0*np.pi/pars['lx']
            kxgrid = np.linspace(-(pars['nx0']/2-1)*kxmin,pars['nx0']/2*kxmin,num=pars['nx0'])
            kxgrid = np.roll(kxgrid,int(pars['nx0']/2+1))
            #print("kxgrid"+str(kxgrid))
            
            #print("kygrid"+str(kygrid))
            zgrid = np.linspace(-np.pi,np.pi,pars['nz0'],endpoint=False)            
    
            apar=field.apar()[:,:,:]
            #print("apar"+str(np.shape(apar)))
            apar_ky = np.sum(apar,axis=2)         #sum over x_axis
            (nz0,nky0)=np.shape(apar_ky)
            B1_ky=np.zeros(np.shape(apar_ky))
            #print("apar_ky"+str(np.shape(apar_ky)))

            B1_ky=ky_GENE_grid*apar_ky*Apar_to_B1 #B1 in Gauss  (nz0,nky0)*(nz0,nky0)*scaler
            
        else:  #x_local = False
            print("Sorry, cannot handle Global Nonlinear yet...")
            pass
        #**Finished reading the Br
        #Recall B1_ky_t_inz=np.zeros((nky0,ntime))

        (nz,nky)=np.shape(B1_ky)
        B1_ky_t_inz[:,i]=B1_ky[inz,:]
    
    ky_GENE_inz = ky_GENE_grid[inz,:]
    
    amplitude_frequency_sum=0
    amplitude_growth_sum=0
    #print(str(B1_ky_t_inz))
    if plot==True:
        ims_B1=[]
    for iky in range(nky):
        B1_inz_t=B1_ky_t_inz[iky,:]
        frequency,amplitude_frequency,amplitude_growth=FFT_function_time(B1_inz_t,time_list,plot=False)
        frequency_kHZ=frequency*gyroFreq/(1000.)

        if plot==True:
            plt.clf()
            plt.plot(frequency_kHZ,amplitude_frequency,label='frequency')
            plt.plot(frequency_kHZ,amplitude_growth,label='growth')
            plt.title(r'B_r(Gauss)'+' at ky_out_board= '+str(ky_GENE_inz[iky]))
            plt.xlabel(r'$f(kHz)$')       
            plt.ylabel(r'$B_r(Gauss)$')
            plt.legend()
            plt.savefig(pic_path+'/B_r_ky_out_board='+str(ky_GENE_inz[iky])+'.png')
            

        if plot==True:
            ims_B1.append(imageio.imread(pic_path+'/B_r_ky_out_board='+str(ky_GENE_inz[iky])+'.png'))



        amplitude_frequency_sum=amplitude_frequency_sum+abs(amplitude_frequency)
        amplitude_growth_sum=amplitude_growth_sum+amplitude_growth

        if output_csv==True:
            d = {'ky_out_board':[ky_GENE_inz[iky]]*len(frequency_kHZ),'frequency(kHZ)':frequency_kHZ,'B_R(Gauss)amplitude_frequency':amplitude_frequency,'B_R(Gauss)amplitude_growth':amplitude_growth}
            df_k=pd.DataFrame(d, columns=['ky_out_board','frequency(kHZ)','B_R(Gauss)amplitude_frequency','B_R(Gauss)amplitude_growth'])
            df_k.to_csv(csv_path+'/B_r_inz='+str(inz)+'ky_out_board='+str(ky_GENE_inz[iky])+'.csv',index=False)
    if plot==True:
        imageio.mimwrite(pic_path+'/0_B_r_inz='+str(inz)+'ky_dynamic_images.gif', ims_B1)

        plt.clf()
        plt.plot(frequency_kHZ,amplitude_frequency_sum,label='frequency')
        plt.plot(frequency_kHZ,amplitude_growth_sum,label='growth')
        plt.title(r'$B_r(Gauss)$'+' sum over all mode numbers')
        plt.xlabel(r'$f(kHz)$')       
        plt.ylabel(r'$B_r(Gauss)$')
        plt.legend()
        plt.savefig(pic_path+'/0Sum_inz='+str(inz)+'B_r_ky_out_board.png') 
        if show==True:
            plt.show()
        

    if output_csv==True:
        d = {'frequency(kHZ)':frequency_kHZ,'B_R(Gauss)amplitude_frequency':amplitude_frequency_sum,'B_R(Gauss)amplitude_growth':amplitude_growth_sum}
        df_sum=pd.DataFrame(d, columns=['frequency(kHZ)','B_R(Gauss)amplitude_frequency','B_R(Gauss)amplitude_growth'])
        df_sum.to_csv(csv_path+'/0Sum_B_r_ky_out_board=.csv',index=False)

    return frequency_kHZ,amplitude_frequency_sum,amplitude_growth_sum


#def LN_apar_frequency_nz_Doppler(suffix,inz,time_start,time_end,plot=False,pic_path='pic',csv_path='csv',output_csv=False,show=False):
def LN_apar_frequency_nz_iky(suffix,inz,iky,time_start,time_end,plot=False,pic_path='pic',csv_path='csv',output_csv=False,show=False):
    #Where inz is the number of the element in nz

    #Import the parameters from parameter file using ParIO
    par = Parameters()
    par.Read_Pars('parameters'+suffix)
    pars = par.pardict
    #getting B field using read_write_geometry.py
    gpars,geometry = read_geometry_local(pars['magn_geometry'][1:-1]+suffix)
    #Get geom_coeff from ParIO Wrapper
    geom_type, geom_pars, geom_coeff = init_read_geometry_file(suffix, pars)
    #Import the field file using fieldlib
    field = fieldfile('field'+suffix,pars)
    time = np.array(field.tfld)  #time stampes

    B_gauss=10.**4              #1T=10^4Gauss
    qref = 1.6E-19              #in C
    c  = 1.                     #in 3*10^8m/s
    m_kg = 1.673E-27            #in kg
    Bref = pars['Bref']         #in Tesla
    Tref = pars['Tref']         #in keV
    nref = pars['nref']         #in 10^(19) /m^3
    Lref = pars['Lref']         #in m
    mref = pars['mref']         #in proton mass(kg)
    q0 = pars['q0']              #unitless, safety factor/q95
    x0 = pars['x0']             #x/a, location
    kymin = pars['kymin']       #in rhoi
    nky0 = pars['nky0']         #in total number of ky
    n_step = pars['n0_global']  #in rhoi
    nref = nref * 1.E19         #in the unit of /m^3
    Tref = Tref * qref * 1.E03  #in the unit of J
    mref = mref * m_kg          #in the unit of kg
    pref = nref * Tref          #in Pa*k_{B}
    cref = np.sqrt(Tref / mref) #in the unit of m/s
    Omegaref = qref * Bref / mref / c  #in rad/s
    rhoref = cref / Omegaref           #in m rho_i(ion gyroradii)
    rhorefStar = rhoref / Lref         #Unitless
    gyroFreq= cref/Lref                 #the facor convert frequency from cs/a to rad/s


    #ky comes from geomWrapper.py
    ky_GENE_temp=ky(pars, geom_coeff,plot=False)     #ky for ky min for differen z
    #print('ky shape: '+str(np.shape(ky_GENE_temp)))

    #Determine the n for kymin
    ky_n1=1.*q0*rhoref/(Lref*x0)  #ky for n=1
    n_min=round(kymin/ky_n1)   #n for ky_min
    if n_min==0:
        n_min=1
    n_list=np.arange(int(n_min),int(n_min+nky0*n_step),int(n_step))

    ky_GENE_n1=ky_GENE_temp/float(n_min)
    ky_GENE_grid = np.outer(ky_GENE_n1,n_list) #outer product of the two vectors
    
    print("kygrid"+str(np.shape(ky_GENE_grid)))
    
    print('n0 list length: '+str(len(n_list)))
    print('n0 list: '+str(n_list))
    
    
    #B1=abs(np.mean(Apar_GENE[z,:])*len(Apar_GENE[z,:])*(ky_GENE_temp[z]/rhoref)*Bref*B_gauss*rhorefStar*rhoref)
    Apar_to_B1=abs((1./rhoref)*Bref*B_gauss*rhorefStar*rhoref)         #B1=Apar*ky_GENE_temp*Apar_to_B1

    
    time_start_index=np.argmin(abs(time - time_start))
    time_end_index=np.argmin(abs(time - time_end))
    time_list = time[time_start_index:time_end_index+1]
    
    nky0=len(n_list)
    ntime=len(time_list)
    B1_ky_t_inz=np.zeros((nky0,ntime))

    if os.path.isdir(csv_path):  #if path does not exist, then create 'csv'
        pass
    else:
        os.mkdir(csv_path) 
    if os.path.isdir(pic_path):  #if path does not exist, then create 'pic'
        pass
    else:
        os.mkdir(pic_path) 
    print("**********Scan starts, output in csv and pic***************")


    for i in range(len(time_list)):
        time0=time_list[i]
        itime = np.argmin(abs(time - time0))
        
        print("Looking at the spectra at time:"+str(time[itime]))
        #This sets the time step you want to read in
        field.set_time(time[itime])
        
        
        if 'x_local' in pars:
            if pars['x_local']:
                x_local = True
            else:
                x_local = False 
        else:
            x_local = True

        if x_local:
            kxmin = 2.0*np.pi/pars['lx']
            kxgrid = np.linspace(-(pars['nx0']/2-1)*kxmin,pars['nx0']/2*kxmin,num=pars['nx0'])
            kxgrid = np.roll(kxgrid,int(pars['nx0']/2+1))
            #print("kxgrid"+str(kxgrid))
            
            #print("kygrid"+str(kygrid))
            zgrid = np.linspace(-np.pi,np.pi,pars['nz0'],endpoint=False)            
    
            apar=field.apar()[:,:,:]
            #print("apar"+str(np.shape(apar)))
            apar_ky = np.sum(apar,axis=2)         #sum over x_axis
            (nz0,nky0)=np.shape(apar_ky)
            B1_ky=np.zeros(np.shape(apar_ky))
            #print("apar_ky"+str(np.shape(apar_ky)))

            B1_ky=ky_GENE_grid*apar_ky*Apar_to_B1 #B1 in Gauss  (nz0,nky0)*(nz0,nky0)*scaler
            
        else:  #x_local = False
            print("Sorry, cannot handle Global Nonlinear yet...")
            pass
        #**Finished reading the Br
        #Recall B1_ky_t_inz=np.zeros((nky0,ntime))

        (nz,nky)=np.shape(B1_ky)
        B1_ky_t_inz[:,i]=B1_ky[inz,:]
    
    ky_GENE_inz = ky_GENE_grid[inz,:]
    
    amplitude_frequency_sum=0
    amplitude_growth_sum=0
    #print(str(B1_ky_t_inz))
    if plot==True:
        ims_B1=[]
    
    B1_inz_t=B1_ky_t_inz[iky,:]
    frequency,amplitude_frequency,amplitude_growth=FFT_function_time(B1_inz_t,time_list,plot=False)
    frequency_kHZ=frequency*gyroFreq/(1000.)

    if plot==True:
        plt.clf()
        plt.plot(frequency_kHZ,amplitude_frequency,label='frequency')
        plt.plot(frequency_kHZ,amplitude_growth,label='growth')
        plt.title(r'B_r(Gauss)'+' at ky_out_board= '+str(ky_GENE_inz[iky]))
        plt.xlabel(r'$f(kHz)$')       
        plt.ylabel(r'$B_r(Gauss)$')
        plt.legend()
        plt.savefig(pic_path+'/B_r_ky_out_board='+str(ky_GENE_inz[iky])+'.png')


    if output_csv==True:
        d = {'ky_out_board':[ky_GENE_inz[iky]]*len(frequency_kHZ),'frequency(kHZ)':frequency_kHZ,'B_R(Gauss)amplitude_frequency':amplitude_frequency,'B_R(Gauss)amplitude_growth':amplitude_growth}
        df_k=pd.DataFrame(d, columns=['ky_out_board','frequency(kHZ)','B_R(Gauss)amplitude_frequency','B_R(Gauss)amplitude_growth'])
        df_k.to_csv(csv_path+'/B_r_inz='+str(inz)+'ky_out_board='+str(ky_GENE_inz[iky])+'.csv',index=False)
    

    return frequency_kHZ,amplitude_frequency,amplitude_growth

#************Sample function line
#omegaDoppler=Doppler_calc(suffix,iky,iterdb_file_name)
def Doppler_calc(suffix,iky,iterdb_file_name):
    #Import the parameters from parameter file using ParIO
    par = Parameters()
    par.Read_Pars('parameters'+suffix)
    pars = par.pardict

    B_gauss=10.**4              #1T=10^4Gauss
    qref = 1.6E-19              #in C
    c  = 1.                     #in 3*10^8m/s
    m_kg = 1.673E-27            #in kg
    Bref = pars['Bref']         #in Tesla
    Tref = pars['Tref']         #in keV
    nref = pars['nref']         #in 10^(19) /m^3
    Lref = pars['Lref']         #in m
    mref = pars['mref']         #in proton mass(kg)
    q0 = pars['q0']              #unitless, safety factor/q95
    x0 = pars['x0']             #x/a, location
    kymin = pars['kymin']       #in rhoi
    nky0 = pars['nky0']         #in total number of ky
    n_step = pars['n0_global']  #in rhoi
    nref = nref * 1.E19         #in the unit of /m^3
    Tref = Tref * qref * 1.E03  #in the unit of J
    mref = mref * m_kg          #in the unit of kg
    pref = nref * Tref          #in Pa*k_{B}
    cref = np.sqrt(Tref / mref) #in the unit of m/s
    Omegaref = qref * Bref / mref / c  #in rad/s
    rhoref = cref / Omegaref           #in m rho_i(ion gyroradii)
    rhorefStar = rhoref / Lref         #Unitless
    gyroFreq= cref/Lref                 #the facor convert frequency from cs/a to rad/s
    
    #Determine the n for kymin
    ky_n1=1.*q0*rhoref/(Lref*x0)  #ky for n=1
    n_min=round(kymin/ky_n1)   #n for ky_min
    if n_min==0:
        n_min=1
    n_list=np.arange(int(n_min),int(n_min+nky0*n_step),int(n_step))

    #**********************Doppler shift**********************************************

    rhot0, te0, ti0, ne0, ni0, nz0, vrot0 = read_iterdb_file(iterdb_file_name)
    uni_rhot = np.linspace(min(rhot0),max(rhot0),len(rhot0)*10.)
    x0_index=np.argmin(abs(uni_rhot-x0))
    vrot_u = interp(rhot0,vrot0,uni_rhot)
    omegaDoppler_kHZ = vrot_u[x0_index]*n_list[iky]/(2.*np.pi*1000.)

    #**********************Doppler shift**********************************************

    return omegaDoppler_kHZ



#************Sample function line
#frequency_kHZ, amplitude_frequency, amplitude_growth=LN_apar_frequency_nz_iky(suffix,inz,iky,time_start,time_end,plot=False,pic_path='pic',csv_path='csv',output_csv=False)
def LN_apar_frequency_nz_iky(suffix,inz,iky,time_start,time_end,plot=False,pic_path='pic',csv_path='csv',output_csv=False):
    #Where inz is the number of the element in nz

    #Import the parameters from parameter file using ParIO
    par = Parameters()
    par.Read_Pars('parameters'+suffix)
    pars = par.pardict
    #getting B field using read_write_geometry.py
    gpars,geometry = read_geometry_local(pars['magn_geometry'][1:-1]+suffix)
    #Get geom_coeff from ParIO Wrapper
    geom_type, geom_pars, geom_coeff = init_read_geometry_file(suffix, pars)
    #Import the field file using fieldlib
    field = fieldfile('field'+suffix,pars)
    time = np.array(field.tfld)  #time stampes

    B_gauss=10.**4              #1T=10^4Gauss
    qref = 1.6E-19              #in C
    c  = 1.                     #in 3*10^8m/s
    m_kg = 1.673E-27            #in kg
    Bref = pars['Bref']         #in Tesla
    Tref = pars['Tref']         #in keV
    nref = pars['nref']         #in 10^(19) /m^3
    Lref = pars['Lref']         #in m
    mref = pars['mref']         #in proton mass(kg)
    q0 = pars['q0']              #unitless, safety factor/q95
    x0 = pars['x0']             #x/a, location
    kymin = pars['kymin']       #in rhoi
    nky0 = pars['nky0']         #in total number of ky
    n_step = pars['n0_global']  #in rhoi
    nref = nref * 1.E19         #in the unit of /m^3
    Tref = Tref * qref * 1.E03  #in the unit of J
    mref = mref * m_kg          #in the unit of kg
    pref = nref * Tref          #in Pa*k_{B}
    cref = np.sqrt(Tref / mref) #in the unit of m/s
    Omegaref = qref * Bref / mref / c  #in rad/s
    rhoref = cref / Omegaref           #in m rho_i(ion gyroradii)
    rhorefStar = rhoref / Lref         #Unitless
    gyroFreq= cref/Lref                 #the facor convert frequency from cs/a to rad/s


    #ky comes from geomWrapper.py
    ky_GENE_temp=ky(pars, geom_coeff,plot=False)     #ky for ky min for differen z
    #print('ky shape: '+str(np.shape(ky_GENE_temp)))

    #Determine the n for kymin
    ky_n1=1.*q0*rhoref/(Lref*x0)  #ky for n=1
    n_min=round(kymin/ky_n1)   #n for ky_min
    if n_min==0:
        n_min=1
    n_list=np.arange(int(n_min),int(n_min+nky0*n_step),int(n_step))

    ky_GENE_n1=ky_GENE_temp/float(n_min)
    ky_GENE_grid = np.outer(ky_GENE_n1,n_list) #outer product of the two vectors
    
    print("kygrid"+str(np.shape(ky_GENE_grid)))
    
    print('n0 list length: '+str(len(n_list)))
    print('n0 list: '+str(n_list))
    
    
    #B1=abs(np.mean(Apar_GENE[z,:])*len(Apar_GENE[z,:])*(ky_GENE_temp[z]/rhoref)*Bref*B_gauss*rhorefStar*rhoref)
    Apar_to_B1=abs((1./rhoref)*Bref*B_gauss*rhorefStar*rhoref)         #B1=Apar*ky_GENE_temp*Apar_to_B1

    
    time_start_index=np.argmin(abs(time - time_start))
    time_end_index=np.argmin(abs(time - time_end))
    time_list = time[time_start_index:time_end_index+1]
    
    nky0=len(n_list)
    ntime=len(time_list)
    B1_ky_t_inz=np.zeros((nky0,ntime))

    if os.path.isdir(csv_path):  #if path does not exist, then create 'csv'
        pass
    else:
        os.mkdir(csv_path) 
    if os.path.isdir(pic_path):  #if path does not exist, then create 'pic'
        pass
    else:
        os.mkdir(pic_path) 
    print("**********Scan starts, output in csv and pic***************")


    for i in range(len(time_list)):
        time0=time_list[i]
        itime = np.argmin(abs(time - time0))
        
        print("Looking at the spectra at time:"+str(time[itime]))
        #This sets the time step you want to read in
        field.set_time(time[itime])
        
        
        if 'x_local' in pars:
            if pars['x_local']:
                x_local = True
            else:
                x_local = False 
        else:
            x_local = True

        if x_local:
            kxmin = 2.0*np.pi/pars['lx']
            kxgrid = np.linspace(-(pars['nx0']/2-1)*kxmin,pars['nx0']/2*kxmin,num=pars['nx0'])
            kxgrid = np.roll(kxgrid,int(pars['nx0']/2+1))
            #print("kxgrid"+str(kxgrid))
            
            #print("kygrid"+str(kygrid))
            zgrid = np.linspace(-np.pi,np.pi,pars['nz0'],endpoint=False)            
    
            apar=field.apar()[:,:,:]
            #print("apar"+str(np.shape(apar)))
            apar_ky = np.sum(apar,axis=2)         #sum over x_axis
            (nz0,nky0)=np.shape(apar_ky)
            B1_ky=np.zeros(np.shape(apar_ky))
            #print("apar_ky"+str(np.shape(apar_ky)))

            B1_ky=ky_GENE_grid*apar_ky*Apar_to_B1 #B1 in Gauss  (nz0,nky0)*(nz0,nky0)*scaler
            
        else:  #x_local = False
            print("Sorry, cannot handle Global Nonlinear yet...")
            pass
        #**Finished reading the Br
        #Recall B1_ky_t_inz=np.zeros((nky0,ntime))

        (nz,nky)=np.shape(B1_ky)
        B1_ky_t_inz[:,i]=B1_ky[inz,:]
    
    ky_GENE_inz = ky_GENE_grid[inz,:]
    
    
    B1_inz_t=B1_ky_t_inz[iky,:]
    frequency_unsort,amplitude_frequency_unsort,amplitude_growth_unsort=FFT_function_time(B1_inz_t,time_list,plot=False)
    frequency_kHZ_unsort=frequency_unsort*gyroFreq/(1000.)

    #For detail reason, check: https://en.wikipedia.org/wiki/Fourier_transform#Conjugation
    #amplitude_frequency=abs(amplitude_frequency) #take amptitude
    
    frequency_kHZ,amplitude_frequency = \
             sort_x_f(frequency_kHZ_unsort,amplitude_frequency_unsort)
    frequency_kHZ,amplitude_growth = \
             sort_x_f(frequency_kHZ_unsort,amplitude_growth_unsort)


    amplitude_frequency=2.*abs(amplitude_frequency.real) #take the real part, take amptitude, then times 2

    if plot==True:
        plt.clf()
        plt.plot(frequency_kHZ,amplitude_frequency,label='frequency')
        plt.plot(frequency_kHZ,amplitude_growth,label='growth')
        plt.title(r'B_r(Gauss)'+' at ky_out_board= '+str(ky_GENE_inz[iky]))
        plt.xlabel(r'$f(kHz)$')       
        plt.ylabel(r'$B_r(Gauss)$')
        plt.legend()
        plt.savefig(pic_path+'/B_r_ky_out_board='+str(ky_GENE_inz[iky])+'.png')



    if output_csv==True:
        d = {'ky_out_board':[ky_GENE_inz[iky]]*len(frequency_kHZ),'frequency(kHZ)':frequency_kHZ,\
            'B_R(Gauss)amplitude_frequency':amplitude_frequency,'B_R(Gauss)amplitude_growth':amplitude_growth}
        df_k=pd.DataFrame(d, columns=['ky_out_board','frequency(kHZ)','B_R(Gauss)amplitude_frequency',\
            'B_R(Gauss)amplitude_growth'])
        df_k.to_csv(csv_path+'/B_r_inz='+str(inz)+'ky_out_board='+str(ky_GENE_inz[iky])+'.csv',index=False)
    

    return frequency_kHZ, amplitude_frequency, amplitude_growth



#from LN_tools import frequency_Doppler
#new_frequency_kHZ, new_amplitude_frequency, new_amplitude_growth=frequency_Doppler(frequency_kHZ,amplitude_frequency,amplitude_growth,omegaDoppler_kHz)
def frequency_Doppler(frequency_kHZ,amplitude_frequency,amplitude_growth,omegaDoppler_kHZ):
    #!!!!!!!!!!Debatable
    #!!!!!!!!!!Debatable
    #!!!!!!!!!!Debatable
    new_amplitude_frequency=amplitude_frequency[::-1]+amplitude_frequency
    new_amplitude_growth=amplitude_growth
    new_frequency_kHZ=frequency_kHZ+omegaDoppler_kHZ
    #!!!!!!!!!!Debatable
    #!!!!!!!!!!Debatable
    #!!!!!!!!!!Debatable
    return new_frequency_kHZ, new_amplitude_frequency, new_amplitude_growth
    
#def LN_apar_frequency_nz_Doppler(suffix,inz,iterdb_file_name,time_start,time_end,plot=False,pic_path='pic',csv_path='csv',output_csv=False,show=False):


#uni_freq,amplitude_frequency_uni=\
#    B1_ky_f_spectrum_Z_sum(suffix,iterdb_file_name,\
#        min_Z0,max_Z0,Outboard_mid_plane,\
#        plot,show,csv_output,pic_path,csv_path)

def B1_ky_f_spectrum_Z_sum(suffix,iterdb_file_name,min_Z0=-0.03,max_Z0=0.03,\
    Outboard_mid_plane=False,plot=False,show=False,csv_output=False,pic_path='pic',csv_path='csv'):
    #Import the parameters from parameter file using ParIO
    par = Parameters()
    par.Read_Pars('parameters'+suffix)
    pars = par.pardict
    
    nky0 = int(pars['nky0'])
    
    #*********Start of Get geometry from magn_geometry***********
    #getting B field using read_write_geometry.py
    gpars,geometry = read_geometry_local(pars['magn_geometry'][1:-1]+suffix)
    #Get geom_coeff from ParIO Wrapper
    geom_type, geom_pars, geom_coeff = init_read_geometry_file(suffix, pars)
    
    real_R=geometry['gl_R'] #it is major radius in meter
    real_Z=geometry['gl_z'] #it is height in meter, midland is 0, down is negative ,up is positive
    
    #*********End of Get geometry from magn_geometry***********
    
    time_start,time_end=start_end_time(suffix,pars)

    
    #******************************************************************
    #********Start of Determin the length of the frequency array****************
    
    iky=nky0-1 #Scan the biggest ky, which has the largest doppler shift
    inz=int(len(real_Z)/2.)
    frequency_kHZ, amplitude_frequency, amplitude_growth=\
        LN_apar_frequency_nz_iky(suffix,inz,iky,time_start,time_end,\
        plot=False,pic_path='pic',csv_path='csv',output_csv=False)

    len_freq=len(frequency_kHZ)
    print("len_freq="+str(len_freq))
    

    #********End of Determin the length of the frequency array****************
    #******************************************************************
    
    #******************************************************************
    #********Start of Determin the length of the nZ****************
    Z_list=[]
    nZ_list=[]
    for nZ in range(len(real_Z)):
        Z=real_Z[nZ]
        if min_Z0<Z and Z<=max_Z0:
            Z_list.append(real_Z[nZ])
            nZ_list.append(nZ)

    if Outboard_mid_plane==True:
        nZ_list=[int(len(real_Z)/2)]
        Z_list=[real_Z[int(len(real_Z)/2)]]

    len_nZ=len(nZ_list)


    print('nZ_list: '+str(nZ_list))
    #********End of Determin the length of the nZ****************
    #******************************************************************
    
    #***********Start of FFT*******************************
    frequency_kHZ_ky=np.zeros((len_nZ,nky0,len_freq))
    amplitude_frequency_ky=np.zeros((len_nZ,nky0,len_freq))
    amplitude_growth_ky=np.zeros((len_nZ,nky0,len_freq))

    for i_Z in range(len_nZ):
        inZ=nZ_list[i_Z]
        Z=real_Z[inZ]
        print('***************************')
        print('***************************')
        print('***************************')
        print('***************************')
        print('Looking at Z='+str(Z)+'m')
        #one can restrict the ky range corresprons to frequency 

        for i_ky in range(nky0):
            amplitude_frequency, amplitude_frequency, amplitude_growth=\
                LN_apar_frequency_nz_iky(suffix,inZ,i_ky,time_start,time_end,\
                plot=False,pic_path='pic',csv_path='csv',output_csv=False)

            omegaDoppler_kHZ=Doppler_calc(suffix,i_ky,iterdb_file_name)

            new_frequency_kHZ_ky, new_amplitude_frequency, \
                new_amplitude_growth=frequency_Doppler(frequency_kHZ,\
                amplitude_frequency,amplitude_growth,omegaDoppler_kHZ)


            frequency_kHZ_ky[i_Z,i_ky,:]=new_frequency_kHZ_ky
            amplitude_frequency_ky[i_Z,i_ky,:]=new_amplitude_frequency
            amplitude_growth_ky[i_Z,i_ky,:]=new_amplitude_growth

    #***********End of FFT*******************************


    #***********Start of Sum of Z--Length-Weighted*************************

    frequency_kHZ_ky_sum_Z=np.zeros((nky0,len_freq))
    amplitude_frequency_ky_sum_Z=np.zeros((nky0,len_freq))
    amplitude_growth_ky_sum_Z=np.zeros((nky0,len_freq))



    for i_ky in range(nky0):
        sum_length_TEMP=0.
        for i_Z in range(len(nZ_list)):
            nZ=nZ_list[i_Z]
            length=np.sqrt( (real_R[nZ]-real_R[nZ-1])**2. \
                   +(real_Z[nZ]-real_Z[nZ-1])**2. )
            sum_length_TEMP=sum_length_TEMP+length
            frequency_kHZ_ky_sum_Z[i_ky,:]=frequency_kHZ_ky_sum_Z[i_ky,:]+frequency_kHZ_ky[i_Z,i_ky,:]*length
            amplitude_frequency_ky_sum_Z[i_ky,:]=amplitude_frequency_ky_sum_Z[i_ky,:]+amplitude_frequency_ky[i_Z,i_ky,:]*length
            amplitude_growth_ky_sum_Z[i_ky,:]=amplitude_growth_ky_sum_Z[i_ky,:]+amplitude_growth_ky[i_Z,i_ky,:]*length

        frequency_kHZ_ky_sum_Z[i_ky,:]=frequency_kHZ_ky_sum_Z[i_ky,:]/sum_length_TEMP
        amplitude_frequency_ky_sum_Z[i_ky,:]=amplitude_frequency_ky_sum_Z[i_ky,:]/sum_length_TEMP
        amplitude_growth_ky_sum_Z[i_ky,:]=amplitude_growth_ky_sum_Z[i_ky,:]/sum_length_TEMP

    #***********End of Sum of Z--Length-Weighted*************************

    #*************End of Interperlation******************
    df_min=min(abs(frequency_kHZ_ky_sum_Z[0,:-1]-frequency_kHZ_ky_sum_Z[0,1:]))
    print("df_min: "+str(df_min))
    print("min(frequency_kHZ_ky_sum_Z): "+str(np.amin(frequency_kHZ_ky_sum_Z)))
    uni_freq = np.linspace(np.amin(frequency_kHZ_ky_sum_Z),\
                           np.amax(frequency_kHZ_ky_sum_Z),\
                           num=int(abs((np.amax(frequency_kHZ_ky_sum_Z)-np.amin(frequency_kHZ_ky_sum_Z))/df_min)*10.))
    len_uni_freq=len(uni_freq)                     
    
    print("len_uni_freq: "+str(len_uni_freq))
    print("frequency_kHZ_ky_sum_Z[i_ky,:]: "+str(len(frequency_kHZ_ky_sum_Z[i_ky,:])))
    print("amplitude_frequency_ky_sum_Z[i_ky,:]: "+str(len(amplitude_frequency_ky_sum_Z[i_ky,:])))

    frequency_kHZ_uni=np.zeros((nky0,len_uni_freq))
    amplitude_frequency_uni=np.zeros((nky0,len_uni_freq))
    new_frequency_kHZ_uni=np.zeros((nky0,len_uni_freq))


    for i_ky in range(nky0):
        frequency_kHZ_uni[i_ky,:]=uni_freq
        amplitude_frequency_uni[i_ky,:]=np.interp(uni_freq,frequency_kHZ_ky_sum_Z[i_ky,:],amplitude_frequency_ky_sum_Z[i_ky,:])
        new_frequency_kHZ_uni[i_ky,:]=np.interp(uni_freq,frequency_kHZ_ky_sum_Z[i_ky,:],frequency_kHZ_ky_sum_Z[i_ky,:])
            

    #*************end of Interperlation******************

    n_list,ky_list=ky_list_calc(suffix)
    
    #****************start of Output***********************
    for i_ky in range(len(n_list)):
        d = {'f(kHz)':frequency_kHZ_ky_sum_Z[i_ky,:],'B_R(Gauss)':amplitude_frequency_ky_sum_Z[i_ky,:]}
        df=pd.DataFrame(d, columns=['f(kHz)','B_R(Gauss)'])
        df.to_csv(csv_path+'/B_r_freq_n_'+str(n_list[i_ky])+'.csv',index=False)
    
        plt.clf()
        plt.plot(frequency_kHZ_ky_sum_Z[i_ky,:],amplitude_frequency_ky_sum_Z[i_ky,:],label='Original')
        plt.xlabel('frequency (kHz)')
        plt.ylabel('B_r(Gauss)') 
        plt.title(r'$\bar{B}_r$(Gauss) spectrogram of n='+str(n_list[i_ky]),fontsize=18)
        plt.savefig(pic_path+'/B_r_freq_n_'+str(n_list[i_ky])+'.png')
        
        plt.clf()
        plt.plot(frequency_kHZ_ky_sum_Z[i_ky,:],amplitude_frequency_ky_sum_Z[i_ky,:],label='Original')
        plt.plot(frequency_kHZ_uni[i_ky,:],amplitude_frequency_uni[i_ky,:],label='Intper',alpha=0.5)
        plt.legend()
        plt.xlabel('frequency (kHz)')
        plt.ylabel('B_r(Gauss)') 
        plt.title(r'$\bar{B}_r$(Gauss) spectrogram of n='+str(n_list[i_ky]),fontsize=18)
        plt.savefig(pic_path+'/Interp_B_r_freq_n_'+str(n_list[i_ky])+'.png')

    
    B1_plot=amplitude_frequency_ky_sum_Z
    f_plot=frequency_kHZ_ky_sum_Z
    ky_plot=np.zeros(np.shape(frequency_kHZ_ky_sum_Z))
    
    for i_ky in range(nky0):
        ky_plot[i_ky,:]=  [ky_list[i_ky]] *len(frequency_kHZ_ky_sum_Z[i_ky,:])

    B1_plot=np.transpose(B1_plot)
    f_plot=np.transpose(f_plot)
    ky_plot=np.transpose(ky_plot)
    
    #print('shape'+str(np.shape(np.transpose(frequency_kHZ_ky_sum_Z))))

    
    if plot==True:
        plt.clf()
        plt.ylabel(r'$k_y \rho_i$',fontsize=10)
        plt.xlabel(r'$f(kHz)$',fontsize=10)
        plt.contourf(f_plot,ky_plot,np.log(B1_plot),cmap='RdGy')
        for ky in ky_list:
            plt.axhline(ky,color='red',alpha=0.5)#alpha control the transparency, alpha=0 transparency, alpha=1 solid
        plt.axhline(ky_list[0],color='red',alpha=0.5,label='n starts from'+str(n_list[0]) )#alpha control the transparency, alpha=0 transparency, alpha=1 solid
        plt.legend()
        plt.colorbar()
        plt.title(r'log($B_r$) contour plot',fontsize=10)
        plt.savefig('0B_r_contour.png')
        #plt.show()


    #****************end of Output***********************
    


    #**********start of Sum over ky*********************
    
    amplitude_frequency_uni_ky_sum=np.sum(amplitude_frequency_uni,axis=0)
    #amplitude_growth_uni_ky_sum=np.sum(amplitude_growth_uni,axis=0)
    
    #**********end of Sum over ky*********************
    if csv_output==True:
        d = {'f(kHz)':uni_freq,'B_R(Gauss)':amplitude_frequency_uni_ky_sum}
        df=pd.DataFrame(d, columns=['f(kHz)','B_R(Gauss)'])
        df.to_csv('0B_r_from_'+str(max_Z0)+'_to_'+str(min_Z0)+'.csv',index=False)

    if plot==True:
        plt.clf()
        plt.xlabel(r'$Frequency(kHz)$',fontsize=15)
        plt.ylabel(r'$\bar{B}_r(Gauss)$',fontsize=15)
        plt.plot(uni_freq,amplitude_frequency_uni_ky_sum,label='Inpter')
        #plt.legend()
        plt.title(r'$\bar{B}_r$(Gauss) spectrogram',fontsize=18)
        plt.savefig('0RIP_freq_spectrogram.png')


    if plot==True: 
        plt.clf()
        plt.plot(uni_freq,amplitude_frequency_uni_ky_sum)
        plt.xlabel('frequency (kHz)')
        plt.ylabel('B_r(Gauss)') 
        plt.title(r'$\bar{B}_r$(Gauss) spectrogram',fontsize=18)
        plt.savefig('0RIP_freq_spectrogram.png')
        if show==True:
            plt.show()


    return uni_freq,amplitude_frequency_uni_ky_sum,amplitude_frequency_uni
    #uni_freq is 1D array
    #amplitude_frequency_uni_ky_sum is 1D array B1(f) length weighted average over Z, sum of ky
    #amplitude_frequency_uni is 2D array B1(ky,f) length weighted average over Z