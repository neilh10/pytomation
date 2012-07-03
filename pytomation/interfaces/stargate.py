"""
File:
        stargate.py

Description:


Author(s):
         Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com

License:
    This free software is licensed under the terms of the GNU public license, Version 1

Usage:

    see /example_use.py

Example:
    see /example_use.py

Notes:
    Protocol
    http://www.jdstechnologies.com/protocol.html

    2400 Baudrate


Created on May , 2012
"""
import threading
import time
from Queue import Queue
from binascii import unhexlify

from .common import *
from .ha_interface import HAInterface


class Stargate(HAInterface):
#    MODEM_PREFIX = '\x12'
    MODEM_PREFIX = ''

    def __init__(self, interface):
        super(Stargate, self).__init__(interface)
        self._modemRegisters = ""

        self._modemCommands = {
                               'send_upb': '\x14',
                               'read_register': '\x12',
                               'write_register': 'x17'
                               }

        self._modemResponse = {'PA': 'send_upb',
                               'PK': 'send_upb',
                               'PB': 'send_upb',
                               'PE': 'send_upb',
                               'PN': 'send_upb',
                               'PR': 'read_register',
                               }

        self.echoMode()

    def _readModem(self, lastPacketHash):
        #check to see if there is anyting we need to read
        responses = self._interface.read()
        if len(responses) != 0:
            print "Response>\n" + hex_dump(responses)
            for response in responses.splitlines():
                responseCode = response[:2]
                if responseCode == 'PA':  # UPB Packet was received by PIM. No ack yet
                    #pass
                    self._processUBP(response, lastPacketHash)
                elif responseCode == 'PU':  # UPB Unsolicited packet received
                    self._processNewUBP(response)
                elif responseCode == 'PK':  # UPB Packet was acknowledged
                    pass
#                    self._processUBP(response, lastPacketHash)
                elif responseCode == 'PR':  # Register read response
                    self._processRegister(response, lastPacketHash)
        else:
            #print "Sleeping"
            #X10 is slow.  Need to adjust based on protocol sent.  Or pay attention to NAK and auto adjust
            #time.sleep(0.1)
            time.sleep(0.5)

    def _processUBP(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['send_upb']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = True

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            del self._pendingCommandDetails[foundCommandHash]
        else:
            print "Unable to find pending command details for the following packet:"
            print hex_dump(response, len(response))

    def _processRegister(self, response, lastPacketHash):
        foundCommandHash = None

        #find our pending command in the list so we can say that we're done (if we are running in syncronous mode - if not well then the caller didn't care)
        for (commandHash, commandDetails) in self._pendingCommandDetails.items():
            if commandDetails['modemCommand'] == self._modemCommands['read_register']:
                #Looks like this is our command.  Lets deal with it
                self._commandReturnData[commandHash] = response[4:]

                waitEvent = commandDetails['waitEvent']
                waitEvent.set()

                foundCommandHash = commandHash
                break

        if foundCommandHash:
            del self._pendingCommandDetails[foundCommandHash]
        else:
            print "Unable to find pending command details for the following packet:"
            print hex_dump(response, len(response))

    def _processNewUBP(self, response):
        pass

    def echoMode(self, timeout=None):
        command = '##%1d\r'
        commandExecutionDetails = self._sendModemCommand(
                             command)
#        return self._waitForCommandToFinish(commandExecutionDetails, timeout=timeout)