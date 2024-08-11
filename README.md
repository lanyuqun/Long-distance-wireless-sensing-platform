1. System requirements  
windows 10 or 11  
[ACE software (Analog Device)](https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-development-platforms/ace-software.html)  
[Keysight IO Libraries Suite](https://www.keysight.com/us/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html)  
Python 3.11
3. Installation guide  
Install ACE software, Keysight IO Suite, and Python on the computer. Within ACE, install the AD5791 plugin (instructions can be found on the [Analog Devices website](https://www.analog.com/cn/resources/evaluation-hardware-and-software/evaluation-boards-kits/EVAL-AD5791.html#eb-relatedsoftware)). Install the necessary Python libraries as specified in the `requirements.txt` file.
The installation process is expected to take approximately half a day.  
4. Demo
In the `main.py` file, fill in the VISA address of the connected E4990A instrument at line 236. Adjust the fitting parameters at line 20 according to the electrical parameters of the reader.
