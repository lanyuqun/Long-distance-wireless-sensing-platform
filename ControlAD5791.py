import ACERemoteController as arc
import DACFunctions as dacfunc
import time

# Constants
board = 'EVAL-AD5791SDZ'
chip = 'AD5791'
# Set the ACE installation path
ace_path = r'C:\Program Files (x86)\Analog Devices\ACE'

AD5791 = arc.establish_connection(board, chip, ace_path)
arc.reset(AD5791)
dacfunc.write_dac_code(AD5791, 0x99000, 20, True) 
dacfunc.remove_output_clamp(AD5791)

resolution = 20

# vol_set = 0
# V_refP = 10.0029
# V_refN = -10.0029
# code = bin((vol_set - V_refN) * (2 ^ 20 - 1) / (V_refP - V_refN))

# while (True):
#     dacfunc.write_dac_code(AD5791, 0x9E040, 20, False)
#     time.sleep(0.001)
#     dacfunc.write_dac_code(AD5791, 0xFE620, 20, False)
#     time.sleep(0.001)

code1 = 0x90000
code2 = 0xF0000
# code = code2
t1 = time.perf_counter()

for i in range(100):
    dacfunc.write_dac_code(AD5791, code1, 20, True)
    dacfunc.write_dac_code(AD5791, code2, 20, True)
    # code = code + 0x0100

t2 = time.perf_counter()
print(t2 - t1)

arc.close_connection(AD5791)
