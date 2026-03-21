import math
import numpy as np
import csv
import os
import pandas as pd
import scipy as sp
from scipy import interpolate
from scipy.interpolate import interp1d
from scipy import signal

def normalize(a):
    b = (a-min(a))/(max(a)-min(a))
    return b

def get_real_position_axis(reference):
    fft_ref = np.fft.fft(reference)
    fft_ref[0: int(np.floor(len(reference)/2) - 1)] = np.zeros(int(np.floor(len(fft_ref) / 2) - 1))
    position_axis = normalize(np.unwrap(-np.angle(np.fft.ifft(fft_ref))))

    return position_axis



def get_calibrated_position_axis(position_axis):
    items = os.listdir(".")
    for names in items:
        if names.endswith("parameters_int.txt"):
            filename = names
    filename = "absolute_filepath\\parameters_int.txt"
    ref = pd.read_csv(filename, sep="\t", header=None)
    first_row = (ref.iloc[0])
    second_row = (ref.iloc[1])

    position_ref = first_row.to_numpy(dtype='float64')
    amplitude_ref = second_row.to_numpy(dtype='float64')

    #items = os.listdir(".")
    #for names in items:
    #    if names.endswith("parameters_scale.txt"):
    #        filename = names

    #ref = pd.read_csv(filename, sep="\t", header=None)
    #first_row = (ref.iloc[0])
    #scale_read = first_row.to_numpy(dtype='float64')

    calibrated_position_axis=[]

    #rel_scale = (scale - scale_read) / 1000000

    #position_axis = position_axis + rel_scale   # shift to reference of the motor
    
    position_axis = np.asarray(position_axis).squeeze()

    factor = np.ceil((np.mean(np.diff(position_axis))) / (np.mean(np.diff(position_ref))))  # ratio between position axes

    f = interpolate.interp1d(position_axis, position_axis, kind='cubic')
    oversmp_pos = f(np.linspace(position_axis[0], position_axis[-1], np.abs(int(factor)) * np.shape(position_axis)[0]))     #oversampled position axis

    f1 = interpolate.interp1d(position_ref, amplitude_ref, kind='cubic')
    ref_interp = f1(oversmp_pos)        #interpolated reference on the position axis

    # Find the peaks of the interpolated reference and it gets their indexes
    locs = signal.find_peaks(ref_interp)
    indexes = locs[0]
    left_index = indexes[0]
    right_index = indexes[-1]

    #calib_pos_axis_overs = Get_real_position_axis.get_real_position_axis(ref_interp) * (
    #        position_axis[-1] - position_axis[0]) + position_axis[0] - rel_scale        #oversampled calibrated position axis

    calib_pos_axis_overs = get_real_position_axis(ref_interp) * (
            position_axis[-1] - position_axis[0]) + position_axis[0] 

    calibrated_position_axis = calib_pos_axis_overs[0:-1:int(factor)]
    calibrated_position_axis = np.array(calibrated_position_axis)

    # Compute the indexes factorized
    left_index = int(np.ceil(indexes[0] / factor))
    right_index = int(left_index + len(calibrated_position_axis) - 1)

    return calibrated_position_axis

    '''
    calibrated_position_axis.append(calib_pos_axis_overs[1])
    downsample_index=int(len(calib_pos_axis_overs)/factor)
    for i in range(1, downsample_index):
        index_value = calib_pos_axis_overs[i * int(factor)]
        calibrated_position_axis.append(index_value)

    calibrated_position_axis = np.array(calibrated_position_axis)

    scale_fact = np.mean(np.diff(position_axis)) / np.mean(np.diff(calibrated_position_axis))   #normalize differentials

    calibrated_position_axis = calibrated_position_axis * scale_fact

    return calibrated_position_axis
    '''


def apodization(interferogram, position_axis, apodization_width):


    index = np.argmin(abs(position_axis))
    left_pos_axis = position_axis[0:index+1]
    right_pos_axis = position_axis[index+1:]

    left_gauss = np.exp(-(np.power(left_pos_axis, 2))/(2*(np.power(left_pos_axis[0]*apodization_width*2, 2))))
    right_gauss = np.exp(-(np.power(right_pos_axis, 2))/(2*(np.power(right_pos_axis[-1]*apodization_width*2, 2))))

    apodization_window = np.concatenate((left_gauss, right_gauss))

    apodized_interferogram = interferogram * apodization_window
    return apodized_interferogram




def scan_range(lambda_mean, res):

    items = os.listdir(".")
    for names in items:
        if names.endswith("parameters_int.txt"):
            filename = names
    filename= "absolute_filepath\\parameters_int.txt"
    ref = pd.read_csv(filename, sep="\t", header=None)
    first_row = (ref.iloc[0])
    ref1 = first_row.to_numpy(dtype='float64')

    low=ref1[0]
    high=ref1[-1]

    alpha = np.radians(10)
    min_e=100.0
    min_o=100.0
    lambda_mean=lambda_mean/1000

    with open('C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini\\Python Scripts\\Tamosauskas-e.csv', 'r') as extraordinary:
        reader = csv.reader(extraordinary)
        my_list = list(reader)
        # print(my_list)

        for i in range(len(my_list)):

            if abs(float(my_list[i][0]) - lambda_mean) < min_e:
                min_e = abs(float(my_list[i][0]) - lambda_mean)
                n_e1 = my_list[i][1]
                n_e0 = my_list[i - 1][1]
                n_e2 = my_list[i + 1][1]
                x0 = my_list[i - 1][0]
                x1 = my_list[i][0]
                x2 = my_list[i + 1][0]

        y = [float(n_e0), float(n_e1), float(n_e2)]
        x = [float(x0), float(x1), float(x2)]

        # print(x)
        # print(y)
        f1 = interpolate.interp1d(x, y, kind='linear')

        n_e = f1(lambda_mean)
        # print(n_e)
        extraordinary.close()

    with open('C:\\Users\\LOQM-PC\\Documents\\GitHub\\tcspc\\gemini\\Python Scripts\\Tamosauskas-o.csv', 'r') as ordinary:
        reader = csv.reader(ordinary)
        my_list = list(reader)
        # print(my_list)

        for i in range(len(my_list)):

            if abs(float(my_list[i][0]) - lambda_mean) < min_o:
                min_o = abs(float(my_list[i][0]) - lambda_mean)
                n_o1 = my_list[i][1]
                n_o0 = my_list[i - 1][1]
                n_o2 = my_list[i + 1][1]
                x0 = my_list[i - 1][0]
                x1 = my_list[i][0]
                x2 = my_list[i + 1][0]

        y = [float(n_o0), float(n_o1), float(n_o2)]
        x = [float(x0), float(x1), float(x2)]

        # print(x)
        # print(y)
        f1 = interpolate.interp1d(x, y, kind='linear')

        n_o = f1(lambda_mean)
        # print(n_o)
        ordinary.close()


    delta_n = n_e-n_o

    max_excursion = np.abs(0.605*lambda_mean ** 2 / (delta_n * res * math.sin(alpha)) ) # in [mm]

    start = -max_excursion
    end = max_excursion

    if start<low:
        start=low
    if end>high:
        end=high

    return start, end




def spectral_calibration():
    items = os.listdir(".")
    for names in items:
        if names.endswith("parameters_cal.txt"):
            filename = names
    filename = "absolute_filepath\\parameters_cal.txt"
    ref = pd.read_csv(filename, sep="\t", header=None)
    first_row = (ref.iloc[0])
    second_row = (ref.iloc[1])
    wavelength = first_row.to_numpy(dtype='float64')
    reciprocal = second_row.to_numpy(dtype='float64')



    P_freq2wave = np.polyfit(reciprocal, 1/wavelength, 7);
    P_wave2freq = np.polyfit(1/wavelength, reciprocal, 7);
    
    return P_freq2wave, P_wave2freq




def freq2wav(freq):
    P_freq2wave, P_wave2freq=spectral_calibration()

    wave=P_freq2wave[1]+P_freq2wave[0]*freq

    return wave




def dft(interf, pos, start_freq, end_freq, samples):
    dpos=np.diff(pos)
    dpos=np.append(dpos,0)
    freq = np.linspace(start_freq, end_freq, samples)  # Creating frequency axis
    pos = pos.reshape(len(pos), 1)
    a = np.exp(-1j * 2 * np.pi * pos * freq)
    b = dpos * interf
    spect = b.dot(a)    # computes the dft

    return spect, freq

def movmean(A, n):
    ser = pd.Series(A)
    data_mean = ser.rolling(window=n, min_periods=1, center=True).mean()

    #moved_averages = pd.DataFrame.to_numpy(data_mean)
    moved_averages = data_mean.to_numpy()

    #moved_averages=np.mean(A)

    return moved_averages


def get_spectrum(interferogram, position_axis, start_wavelength, end_wavelength, samples, apodization_width):
    # Load spectral calibration file
    items = os.listdir(".")

    for names in items:
        if names.endswith("parameters_cal.txt"):
            filename = names
    filename = "absolute_filepath\\parameters_cal.txt"
    ref = pd.read_csv(filename, sep="\t", header=None)
    first_row = (ref.iloc[0])
    second_row = (ref.iloc[1])
    wavelength = first_row.to_numpy(dtype='float64')
    reciprocal = second_row.to_numpy(dtype='float64')

    # Compute the frequency limits from the calibration file
    fn = interp1d(1 / wavelength, reciprocal, kind="linear")
    start_freq = fn(1 / end_wavelength)
    end_freq = fn(1 / start_wavelength)
    np.reshape(interferogram, len(interferogram))

    '''
    P_freq2wave, P_wave2freq = Spectral_calibration.spectral_calibration()
    start_freq = np.polyval(P_wave2freq, 1 / end_wavelength)
    end_freq = np.polyval(P_wave2freq, 1 / start_wavelength)
    '''



    array_mean_move = movmean(interferogram, int(len(interferogram) / 5))

    signal = apodization(interferogram - array_mean_move, position_axis, apodization_width)
    signal_ph = apodization(interferogram - array_mean_move, position_axis, apodization_width * 0.1)

    spect_mod, freq = dft(signal, position_axis, start_freq, end_freq, samples)
    spect_ph, freq = dft(signal_ph, position_axis, start_freq, end_freq, samples)

    spectrum = np.real(spect_mod * np.exp(-1j * np.angle(spect_ph)))

    # Compute the calibrated wavelength axis
    fn = interp1d(reciprocal, 1 / wavelength, kind="linear")
    wave = 1 / fn(freq)
    #wave = 1 / np.polyval(P_freq2wave, freq)

    return spectrum, wave, freq, signal




def wav2freq(wave_lambda):
    P_freq2wave, P_wave2freq=spectral_calibration()

    freq_mm=P_wave2freq[1]+P_wave2freq[0]/wave_lambda

    return freq_mm
