# Copyright (c) 2019 Analog Devices, Inc.  All rights reserved.

# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   - Redistributions of source code must retain the above copyright notice, this
#     list of conditions and the following disclaimer.
#   - Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#   - Modified versions of the software must be conspicuously marked as such.
#   - This software is licensed solely and exclusively for use with
#     processors/products manufactured by or for Analog Devices, Inc.
#   - This software may not be combined or merged with other code in any manner
#     that would cause the software to become subject to terms and conditions
#     which differ from those listed here.
#   - Neither the name of Analog Devices, Inc. nor the names of its contributors
#     may be used to endorse or promote products derived from this software
#     without specific prior written permission.
#   - The use of this software may or may not infringe the patent rights of one
#     or more patent holders.  This license does not release you from the
#     requirement that you obtain separate licenses from these patent holders
#     to use this software.

# THIS SOFTWARE IS PROVIDED BY ANALOG DEVICES, INC. AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# NON-INFRINGEMENT, TITLE, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.
#
# IN NO EVENT SHALL ANALOG DEVICES, INC. OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, DAMAGES ARISING OUT OF CLAIMS OF INTELLECTUAL
# PROPERTY RIGHTS INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import clr
import sys
# Import relevant objects from the ACE remote client DLL
# This MUST be done after importing CLR


def establish_connection(board, chip, ace_path):
    """Establishes connection with the ACE Plugin and sets the appropriate context
    
    Parameters
    ----------
    board : str
        Name of the Evalauation Board.
    chip : str
        Name of the desired Chip present on the evalauation Board.
    ace_path : str
        Path of installation of ACE.

    Returns
    -------
    clientSupport
        Reference to the connection to the ACE Application.
    """

    # Set your ACE installation directory.
    sys.path.append(ace_path + r'\Client')
    clr.AddReference('AnalogDevices.Csa.Remoting.Clients')
    import AnalogDevices.Csa.Remoting.Clients as __adrc
    # Create connection to ACE. Remember to enable the server
    # in tools->settings->IPC Server.
    clr.AddReference('AnalogDevices.Csa.Remoting.Clients')
    __clientManager = __adrc.ClientManager.Create()
    # Use the port address set in the ACE IPC Server settings here:
    __clientSupport = __clientManager.CreateRequestClient('localhost:2357')
    __clientSupport.AddHardwarePlugin(board)
    __clientSupport.set_ContextPath(r'\System\Subsystem_1' + '\\' + board)
    reset(__clientSupport)
    __clientSupport.set_ContextPath(r'\System\Subsystem_1' + '\\' + board + '\\' + chip)
    # Refer to ACE remote API documentation for more details.
    return __clientSupport


def write_to_bitfield(client, bitfieldname, val):
    """Write data to a device bitfield.

    Parameters
    ----------
    client
        Reference to the connection to the ACE Application.
    bitfieldname : str
        Name of the bitfield as seen in the Memorymap within ACE.
    val : int
        Integer value of data to be written.
    """

    client.SetBitfield(bitfieldname, val)
    client.Run('@ApplySettings')
    return


def reset(client):
    """Resets the device and gets it to a known state.

    Parameters
    ----------
    client
        Reference to the connection to the ACE Application.
    """

    client.Run('@Reset')
    # write_to_bitfield(client, "OPGND", 0)
    return


def close_connection(client):
    """Releases the connection to the ACE Application.

    Parameters
    ----------
    client
        Reference to the connection to the ACE Application.
    """

    client.CloseSession()
    return
