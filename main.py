import pyvisa
import ACERemoteController as arc
import DACFunctions as dacfunc
import os
import time
from datetime import datetime
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import scipy.optimize as op
from scipy.ndimage import gaussian_filter1d as ft
from scipy.signal import find_peaks as fp
import traceback

matplotlib.use('TkAgg')
SWEEP_POINT = 0  # a global variable for the the sweep points
SWEEP_TYPE = 0  # 0 - bus, 1 - internal

FITTED_PARA = [
    13e-6, 22e-12, 53e3
]  # inductance, capacitance, resistance  [13e-6, 20e-12, 46e3] [13e-6, 29e-12, 54e3]
STARTF = 8e6
STORTF = 11e6

SWEEP_POINT_NUM = 250

remark = 'P'  # remarks in the file name


def configBasic(inst, mType1='Z'):  # , mType2='TZ', vol=500e-3
    trace1MeasType = mType1
    apertureDuration = 1
    # Configure Trigger Source to support single trigger with synchronization
    # inst.write("TRIGger1:SOURce BUS")
    inst.write("TRIGger1:SOURce BUS")
    inst.write("INITiate1:CONTinuous ON")
    # Set the aperture which affects trace noise and repeatability, i.e. averaging
    inst.write("SENSe:APERture " + str(apertureDuration))
    # Select trace 1 and set measurement format
    inst.write("CALCulate:PARameter1:DEFine " + trace1MeasType)
    # Set OSC level
    inst.write(":SOUR1:VOLT 1000E-3")  # Max 1V, quan - mV
    # Set data format to binary bin block as real 64-bit
    inst.write("FORMat:DATA REAL"
               )  # REAL: IEEE 64-bit floating point binary transfer format
    inst.write("TRIG1:POIN1 ON")
    # turn off the display update of all windows
    inst.write(':DISPlay:ENABle %d' % (0))
    return


def triggerBasicSweep(inst, startfreq, stopfreq, n=601, sp_t=1000):
    # Set the start and stop frequencies via concatenated string and use of SCPI SENSe FREQuency branch
    inst.write("SENS:FREQ:STAR " + str(startfreq) + ";STOP " + str(stopfreq))
    # If the required sweep points are changed,
    global SWEEP_POINT, SWEEP_TYPE
    if (abs(n - SWEEP_POINT) > 0.5):
        # Set the number of trace points
        inst.write("SENSe:SWEep:POINts " + str(n))
        SWEEP_POINT = n
    if sp_t != 1000:
        if SWEEP_TYPE == 0:
            inst.write("TRIGger1:SOURce internal")
            SWEEP_TYPE = 1
        # wait for sweep to complete
        time.sleep(sp_t)
    else:
        if SWEEP_TYPE == 1:
            inst.write("TRIGger1:SOURce BUS")
            SWEEP_TYPE = 0
        # inst.write("TRIG")
        # Force single trigger with hold-off.
        inst.query("TRIG:SING;*OPC?")
    # Query Trace stimulus arrays as Real64-bit binary blocks.
    trace1Data = inst.query_binary_values("CALC:DATA:FDATA?",
                                          datatype='d',
                                          is_big_endian=True)
    stimulusData = np.linspace(startfreq, stopfreq, n)
    # For each of the formatted response or data arrays every other
    # value is a zero place holder thus strip this
    trace1DataTrimmed = trace1Data[0::2]
    return trace1DataTrimmed, stimulusData


def C2F_func(p, x):
    '''relationship between Code and resonant frequency'''
    # a1, a2, b1, b2 = p
    # return a1 * np.exp(a2 * x) + b1 * np.exp(b2 * x)
    return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(
        x, 3) + p[4] * np.power(x, 4) + p[5] * np.power(x, 5)


def F2Z_func(p, freq):
    '''relationship between frequency and impedance'''
    L, C, R = p
    Real = 1 / R
    Vir = 1j * 2 * np.pi * freq * C - 1j / (2 * np.pi * freq * L)
    return np.abs(
        1 / (Real + Vir)) - 1e12 * (R < 0)  # R should not small than zero


def F2T_func(p, freq):
    '''relationship between frequency and phase'''
    L, C, R = p
    Real = R
    Vir = 2 * np.pi * freq * L - 1 / (2 * np.pi * freq * C)
    return np.arctan(Vir / Real)


def Error(p, func, x, y):  # for the calculation of optimize.leastsq
    return func(p, x) - y


def saveFileStr(lable: str,
                remark: str,
                tp: str,
                format: int = 1):  # for convenient save file
    if format == 1:
        testTime = datetime.now().strftime('%m-%d_%H-%M-%S.%f')
    else:
        testTime = datetime.now().strftime('%m-%d_%H')
    saveDir = './res/'
    if remark != '':
        remark = '_' + remark
    return f'{saveDir}{lable}_{testTime}{remark}.{tp}'


def C2F_Calibr(inst_E,
               inst_AD,
               startfreq=3.5e6,
               stopfreq=5.5e6,
               sp=201,
               startC=0x99000,
               stopC=0xFF000,
               stepC=0x03000):
    F1 = startfreq  # for dynamical update of the sweep range
    F2 = stopfreq
    sweepPoint = sp
    Code2Freq = []
    startCode = startC
    stopCode = stopC  # the max code to test
    stepCode = stepC  # the step code
    setCode = startCode
    # Find the relationship between the applied code and the resonant frequency
    dacfunc.write_dac_code(inst_AD, setCode, 20, True)
    while setCode <= stopCode:
        # Apply the code
        dacfunc.write_dac_code(inst_AD, setCode, 20, True)
        time.sleep(0.005)
        # Perform a measurement
        imp, freq = triggerBasicSweep(inst_E, F1, F2, sweepPoint)
        # Fit the sweep result and find the resonant frequency
        p_est, t = op.leastsq(Error, FITTED_PARA, args=(F2Z_func, freq, imp))
        peakF = op.fminbound(lambda freq: -F2Z_func(p_est, freq), F1, F2)
        # Save the code and the corresponding resonant frequency
        if (peakF > startfreq * 1.01
                and peakF < stopfreq * 0.99):  # valid data
            Code2Freq.append(
                [int(setCode),
                 peakF])  # [:, 0] is code, [:, 1] is resonant frequency
        # print([setCode, peakF])
        # Increase the code to apply
        setCode = setCode + stepCode
        # time.sleep(0.003)
        F1 = int(max(startfreq, peakF * 0.95))
        F2 = int(min(stopfreq, peakF * 1.15))
    # Convert the list to np array
    C2F_np = np.array(Code2Freq)
    # Fit the data with preset function "C2F_func"
    para_C2F = op.leastsq(Error, [-2.8e7, 170e2, 3e-4, 4e-10, -2e-16, 4e-23],
                          args=(C2F_func, C2F_np[:, 0], C2F_np[:, 1]))
    para_C2F = para_C2F[0]
    np.savetxt(saveFileStr('C2F', '', 'txt', 0),
               C2F_np,
               header=str(para_C2F)[1:-1],
               comments='')
    # Plot the relationship between the code and the resonant frequency
    fig, ax = plt.subplots()
    # ax = fig.add_subplots(111)
    p1 = ax.plot(C2F_np[:, 0], C2F_np[:, 1], c='#003366',
                 label='measured')  # p =
    p2 = ax.plot(C2F_np[:, 0],
                 C2F_func(para_C2F, C2F_np[:, 0]),
                 '--',
                 c='#cc3333',
                 label='fitted')  # p =
    ax.set_xlabel("Code")
    ax.set_ylabel("resonant frequency (Hz)")
    ax2 = ax.twinx()
    p3 = ax2.plot(C2F_np[:, 0],
                  (C2F_func(para_C2F, C2F_np[:, 0]) - C2F_np[:, 1]) /
                  C2F_np[:, 1] * 100,
                  '-r',
                  label='error')
    ax2.set_ylabel("Error (%)")
    p = p1 + p2 + p3
    labs = [kk.get_label() for kk in p]
    ax.legend(p, labs, loc=0)
    # plt.ion()
    # plt.ioff()
    # plt.xlabel('Code')
    # plt.ylabel('resonant frequency (Hz)')
    fig.savefig(saveFileStr('C2F', remark, 'png'))
    plt.show()
    plt.close()
    return para_C2F, C2F_np


# #########################################################################################################################

os.add_dll_directory(r"C:/Program Files/Keysight/IO Libraries Suite/bin")
os.add_dll_directory(r"C:/Program Files (x86)/Keysight/IO Libraries Suite/bin")
rm = pyvisa.ResourceManager(
    "C:\\Program Files (x86)\\IVI Foundation\\VISA\\WinNT\\ktvisa\\ktbin\\visa32.dll"
)  # kt or ag?

startCode = 0x99000
stopCode = 0xE6600  # 0xF9900  # E658B
stepCode = 0x02000
startFrequency = STARTF
stopFrequency = STORTF
sweepPoint = 201

board = 'EVAL-AD5791SDZ'
chip = 'AD5791'
# Set the ACE installation path
ace_path = r'C:\Program Files (x86)\Analog Devices\ACE'
AD5791 = arc.establish_connection(board, chip, ace_path)
arc.reset(AD5791)
# Set the output voltage to around 1.95V FIRST!
dacfunc.write_dac_code(AD5791, 0x99000, 20, True)
# Enable the voltage output
dacfunc.remove_output_clamp(AD5791)

try:
    E4990A = rm.open_resource('???::?????::?????::??::?::INSTR')  # Fill in a VISA address!!!!!!!!!!!!
    E4990A.timeout = 10000
    configBasic(E4990A)

    exist_C2F = 0
    para_C2F = []
    C2F_np = []
    name = saveFileStr('C2F', '', 'txt', 0)
    while exist_C2F != 1:
        for dirpath, dirname, filename in os.walk("./res/"):
            if name[6:] in filename:
                exist_C2F = 1
                t = input(
                    f"Find the C2F file '{name}'. Open it? <Y/N/filename>: ")
                if t in {'Y', 'y', 'yes', ''}:
                    with open(name, 'r') as f:
                        data = f.readlines()
                        para_C2F = para_C2F + list(map(float, data[0].split()))
                        para_C2F = para_C2F + list(map(float, data[1].split()))
                        for i in data[2:]:
                            C2F_np.append(list(map(float, i.split())))
                    C2F_np = np.array(C2F_np)
                    exist_C2F = 1
                    break
                elif t in {'N', 'n', 'no'}:
                    para_C2F, C2F_np = C2F_Calibr(E4990A, AD5791,
                                                  startFrequency,
                                                  stopFrequency, sweepPoint,
                                                  startCode, stopCode,
                                                  stepCode)
                    exist_C2F = 1
                    break
                else:
                    name = "./res/" + t
                    exist_C2F == 0.5
                    break
        if exist_C2F == 0:
            t = input(
                "Cannot find the C2F file. Please enter the file name or press ENTER to execute calibration. <ENTER/filename>: "
            )
            if len(t) == 0:
                para_C2F, C2F_np = C2F_Calibr(E4990A, AD5791, startFrequency,
                                              stopFrequency, sweepPoint,
                                              startCode, stopCode, stepCode)
                exist_C2F = 1
            else:
                name = "./res/" + t

    time.sleep(1)
    # Select trace 1 and set measurement format
    E4990A.write("CALCulate:PARameter1:DEFine TZ")

    sweepStop = int(np.max(C2F_np[:, 1]) * 0.998) - 1.0
    sweepstart = int(np.min(C2F_np[:, 1]) * 1.0001) + 1.0
    sweepPointNum = SWEEP_POINT_NUM
    sweepStep = round((sweepStop - sweepstart) / sweepPointNum)
    sweepRepeat = 15
    guessCode = min(C2F_np[:, 0])
    remark_loop = remark
    while 1:
        t1 = time.perf_counter()
        sweepFreq = sweepstart
        Freq2Imp = []

        while sweepFreq <= sweepStop:
            # Calculate the float solution of expected code; * 1.005
            rootCode = op.fsolve(
                lambda c: (C2F_func(para_C2F, c) - sweepFreq * 1.002),
                guessCode)[0]
            # Convert the solution to decimal value
            rootCode = int(np.around(rootCode))
            # Prevent the unexpected applied voltage
            if (rootCode < startCode or rootCode > stopCode):
                print(
                    f'Code = {rootCode} is out of range [{startCode}: {stopCode}]!'
                )  # raise Exception
                break
            # t_t1 = time.perf_counter()
            dacfunc.write_dac_code(AD5791, rootCode, 20, True)
            # t_t2 = time.perf_counter()
            # time.sleep(0.030)
            phase, freq = triggerBasicSweep(E4990A, sweepFreq, sweepFreq,
                                            sweepRepeat)
            # t_t3 = time.perf_counter()
            # print(f'--time: {t_t2 - t_t1} s, {t_t3 - t_t2} s')
            tPhase = np.average(phase)
            Freq2Imp.append([sweepFreq, tPhase, rootCode] + phase)
            # print([sweepFreq, tPhase, rootCode])
            sweepFreq = sweepFreq + sweepStep

        t2 = time.perf_counter()
        print(f'time: {t2 - t1} s')

        F2I_np = np.array(Freq2Imp)
        phase_f = ft(F2I_np[:, 1], 2)
        kk = fp(-phase_f, prominence=0.05)
        kk = kk[0]
        if len(kk) == 0:
            kk = 0
        np.savetxt(saveFileStr('F2I', remark_loop, 'txt'),
                   F2I_np,
                   header=f'time, {t1}, {t2}')

        fig, ax = plt.subplots()
        ax.plot(F2I_np[3:, 0], F2I_np[3:, 1], c='#77A88D')
        ax.plot(F2I_np[3:, 0], phase_f[3:], c='y', ls='--')
        ax.plot(F2I_np[kk, 0], phase_f[kk], 'r^')
        print(F2I_np[kk, 0])

        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Phase (°)')
        # p2 = plt.plot(F2I_np[3:, 0], F2I_np[3:, 1], c='#77A88D')
        # plt.ioff()
        # plt.xlabel('Frequency (Hz)')
        # plt.ylabel('Phase (°)')
        fig.savefig(saveFileStr('F2I', remark_loop, 'png'))
        plt.show()

        t = input('continue?')
        if t in {'0', 'n', 'no', 'N'}:
            break
        elif len(t) != 0:
            if t[0] == '_':
                remark_loop = remark + t
            else:
                remark_loop = remark
        else:
            remark_loop = remark

except Exception as ex:
    traceback.print_exc()
    print(ex)

finally:
    E4990A.write(':DISPlay:ENABle %d' % (1))
    E4990A.write("SENSe:SWEep:POINts " + str(201))
    E4990A.write("CALCulate:PARameter1:DEFine " + 'Z')
    E4990A.write("SENS:FREQ:STAR " + str(5e6) + ";STOP " + str(10e6))
    E4990A.write("TRIGger1:SOURce internal")
    E4990A.close()
    arc.close_connection(AD5791)
