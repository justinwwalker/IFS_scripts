import numpy as np
import matplotlib.pyplot as plt
from interp import interp
#Un-uniform FFT: https://scicomp.stackexchange.com/questions/593/how-do-i-take-the-fft-of-unevenly-spaced-data

def FFT_function_time_uniform(function,time,timestep,plot):
    
    norm=1./float(len(time))  #normalizing factor
    
    amplitude_complex = np.fft.fft(function)
    #print(str(time.shape[-1]))
    #output_x = np.fft.fftfreq(t.shape[-1])
    frequency = np.fft.fftfreq(time.shape[-1], d=timestep)
    amplitude_frequency=norm*amplitude_complex.real
    amplitude_growth=norm*amplitude_complex.imag

    if plot==True: 
        plt.clf()
        plt.ylabel(r'$function$',fontsize=10)
        plt.xlabel(r'$time$',fontsize=10)
        plt.plot(time,function)
        plt.title('Function of time',fontsize=20)
        plt.show()

        plt.clf()
        plt.ylabel(r'$amplitude$',fontsize=10)
        plt.xlabel(r'$frequency$',fontsize=10)
        #plt.axvline(frequency,color='red', label="correct frequency")
        #plt.axvline(2.*frequency,color='red', label="correct frequency")
        plt.plot(frequency,amplitude_frequency,label="frequency")
        plt.plot(frequency,amplitude_growth,label="growth")
        plt.legend()
        plt.title('Function of frequency',fontsize=20)
        plt.show()

    return frequency,amplitude_frequency,amplitude_growth


def FFT_function_time_not_uniform(function,time,plot):
    dt=time[:-1]-time[1:]
    

    dt_min=min(dt)

    print('length of the time: '+str(float(int(abs((max(time)-min(time))/dt_min)*1.2))))
    uni_time = np.linspace(min(time),max(time),int(abs((max(time)-min(time))/dt_min)*1.2)) #uniform time
    uni_function = interp(time,function,uni_time)

    dt=time[:-1]-time[1:]
    timestep=dt[0]
    
    frequency,amplitude_frequency,amplitude_growth=FFT_function_time_uniform(uni_function,uni_time,timestep,plot)
    return frequency,amplitude_frequency,amplitude_growth


def FFT_function_time(function,time,plot=False): 
    dt=time[1:]-time[:-1]

    #plt.clf()
    #plt.ylabel(r'$n$',fontsize=10)
    #plt.xlabel(r'$dt$',fontsize=10)
    #plt.plot(time[1:])
    #plt.plot(time[:-1])
    #plt.plot(dt)
    #plt.title('dt',fontsize=20)
    #plt.show()

    if abs(np.std(dt))<min(dt)*0.0000001:
        timestep=dt[0]
        print('time step is uniform, dt=: '+str(timestep))
        print('Runing uniform FFT')
        frequency,amplitude_frequency,amplitude_growth=FFT_function_time_uniform(function,time,timestep,plot)
    else:
        print('time step is NOT uniform. Runing non-uniform FFT')
        frequency,amplitude_frequency,amplitude_growth=FFT_function_time_not_uniform(function,time,plot)

    return frequency,amplitude_frequency,amplitude_growth

#*********Demo function****************
timestep0=0.002
time = np.arange(0.,2.,timestep0)

time = np.array(time)
  
time = np.append(time, [2.001])
print(str(time))
#time.append(2.001)
#time.extend(time)

frequency=20.
omega = 2.*np.pi*frequency
function=np.exp(1.j * omega * time)+0.5*np.exp(1.j * 2*omega * time)
#*********Demo function****************

#frequency,amplitude_frequency,amplitude_growth = FFT_function_time(function,time,plot=True)


