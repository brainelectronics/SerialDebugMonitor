#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# ----------------------------------------------------------------------------
#
# ****************************************************************************
# (c) Copyright by brainelectronics/ElectronicFuture, ALL RIGHTS RESERVED
# ****************************************************************************
#
#  @author       brainelectronics (info@brainelectronics.de)
#  @file         serialDebugMonitor.py
#  @date         June, 2020
#  @version      0.3.0
#  @brief        Connect to Service Reader and test commands or functions
#
#   usage: python2/python3 serialDebugMonitor.py
# ----------------------------------------------------------------------------
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

import logging
import datetime
import json
import queue
import random

import serial
import serial.tools.list_ports as port_list
from serial import SerialException

import threading

import wx
import time
from wx import TextCtrl
from wx import adv

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade


class frmSerialMonitor(wx.Frame):
    # txtSerialMonitor = None  # type: TextCtrl

    def __init__(self, *args, **kwds):
        logFormat = "[%(asctime)s] [%(levelname)-8s] [%(filename)-20s @ %(funcName)-15s:%(lineno)4s] %(message)s"
        logging.basicConfig(format=logFormat, level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.startTime = datetime.datetime.now()    # time of application start
        self.logger.debug("Starting app at %s ..." %self.startTime)

        # begin wxGlade: frmSerialMonitor.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE

        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((800, 600))
        self.SetBackgroundColour("WHITE")

        # define default baudrate and port name (can be part of port's name)
        defaultBaudrate = 921600
        self.defaultPort = "usbmodem1421"

        # create list of available baudrates
        availableBaudrates = [300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 74880, 115200, 230400, 250000, 500000, 921600, 1000000, 2000000]

        # convert values of list to string
        availableBaudrates = [str(x) for x in availableBaudrates]

        # comboBox selection is done by index, -1 is None/empty selection
        self.defaultBaudrateIndex = -1

        if str(defaultBaudrate) in availableBaudrates:
            # get index of defaultBaurate if in the availableBaudrates list
            self.defaultBaudrateIndex = availableBaudrates.index(str(defaultBaudrate))
        else:
            self.logger.warning("Specified defaultBaudrate is not available for selection, using None/empty")

        # create empty list of available ports
        self.availablePorts = list()

        # Combo Box for available Baudrates
        self.cmbBaudRate = wx.ComboBox(
            self, wx.ID_ANY,
            choices=availableBaudrates,
            style=wx.CB_DROPDOWN | wx.CB_READONLY)

        # yet empty Combo Box of Serial Ports
        self.cmbPorts = wx.ComboBox(
            self, wx.ID_ANY,
            choices=self.availablePorts,
            style=wx.CB_DROPDOWN | wx.CB_READONLY)

        # Refresh Serial Ports button
        self.btnRefreshPorts = wx.Button(
            self,
            wx.ID_ANY,
            "Refresh")
        self.btnConnect = wx.Button(
            self,
            wx.ID_ANY,
            "Connect")

        # Text Box of incoming serial data
        self.txtSerialMonitor = wx.TextCtrl(
            self,
            wx.ID_ANY,
            "",
            style=wx.TE_MULTILINE | wx.TE_READONLY)

        self.item_list = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN)

        # most left column of sources list (wx.ListCtrl)
        self.item_list.InsertColumn(
            col=0,
            heading="Type",
            width=100)

        self.item_detail_list = wx.ListCtrl(
            self,
            # size = (-1 , - 1),
            style=wx.LC_REPORT | wx.BORDER_SUNKEN)

        # define columns of this list, access by index
        self.item_detail_list.InsertColumn(
            col=0,
            heading="Key")
        self.item_detail_list.InsertColumn(
            col=1,
            heading="Value")

        self.txtSubmitString = wx.TextCtrl(
            self,
            wx.ID_ANY,
            "")
        self.txtSubmitString.Disable()

        self.btnSubmit = wx.Button(
            self,
            wx.ID_ANY,
            "Submit")
        self.btnSubmit.Disable()

        self._receivingThread = None
        self._runReadThread = False
        self._conn = None
        self._recievedQueue = queue.Queue()
        self.maxSerialChars = 10*1000

        self.debugInfoDict = dict()

        self.redrawTimer = wx.Timer(self)
        self.comTimer = wx.Timer(self)

        self.activeUserSelection = dict()
        self.activeUserSelection["item"] = 0
        self.activeUserSelection["detail"] = 0

        self.__set_properties()
        self.__do_layout()
        self.__create_menu()
        self.CreateStatusBar() # Statusbar at the bottom of the window
        self.__bindEvents()
        # self.__bindTimer()

    def __bindEvents(self):
        self.Bind(
            wx.EVT_COMBOBOX,
            self.OnBaudRateChanged,
            self.cmbBaudRate)

        self.Bind(
            wx.EVT_COMBOBOX,
            self.OnPortChanged,
            self.cmbPorts)

        self.Bind(
            wx.EVT_BUTTON,
            self.OnRefreshPorts,
            self.btnRefreshPorts)

        self.Bind(
            wx.EVT_BUTTON,
            self.OnConnectTarget,
            self.btnConnect)

        self.Bind(
            wx.EVT_BUTTON,
            self.OnSubmit,
            self.btnSubmit)

        self.Bind(
            wx.EVT_CHAR_HOOK,
            self.OnKey)

        self.item_list.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            self.OnDebugItemSelected)

        self.item_detail_list.Bind(
            wx.EVT_LIST_ITEM_SELECTED,
            self.OnDetailSelected)

        self.Bind(
            wx.EVT_PAINT,
            self.OnPaint)

    """
    def __bindTimer(self):
        #  Bind(self, event, handler, source=None, id=wx.ID_ANY, id2=wx.ID_ANY)

        # self.Bind(
        #     event=wx.EVT_TIMER,
        #     handler=self.getAllDebugItems,
        #     source=self.redrawTimer)
        # self.redrawTimer.Start(1000) # update every redrawIntervall
    """

    def __set_properties(self):
        self.SetTitle("EVSE Serial Debug Monitor")

    def __do_layout(self):
        szrMain = wx.BoxSizer(wx.VERTICAL)

        # add horizontal box sizer containing serial ports and refresh button
        szrPorts = wx.BoxSizer(wx.HORIZONTAL)
        szrPorts.Add(
            self.cmbPorts,
            proportion=1,
            border=15,
            flag=wx.EXPAND
            # flag=wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND,
            )
        szrPorts.Add(
            self.btnRefreshPorts,
            proportion=0,
            border=15,
            flag=wx.EXPAND,
            # flag=wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND,
            )
        szrPorts.Add(
            self.btnConnect,
            proportion=0,
            border=15,
            flag=wx.EXPAND
            # flag=wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND,
            )

        # add horizontal box sizer containing list view of serial data
        szrList = wx.BoxSizer(wx.HORIZONTAL)
        szrList.Add(
            self.item_list,
            proportion=0,
            flag=wx.ALL | wx.EXPAND)
        szrList.Add(
            self.item_detail_list,
            proportion=1,
            flag=wx.ALL | wx.EXPAND)

        # add szrPorts to main box sizer
        szrMain.Add(
            szrPorts,
            proportion=0,
            flag=wx.EXPAND,
            border=10)

        # add combo box of baudrate to main box sizer
        szrMain.Add(
            self.cmbBaudRate,
            proportion=0,
            flag=wx.EXPAND,
            border=10)

        # add text view of incomming data to main box sizer
        szrMain.Add(
            self.txtSerialMonitor,
            proportion=1,
            flag=wx.EXPAND,
            border=10)

        # add szrList to main box sizer
        szrMain.Add(
            szrList,
            proportion=0,
            flag=wx.EXPAND,
            border=10)

        # add text input for outgoing data to main box sizer
        szrMain.Add(
            self.txtSubmitString,
            proportion=0,
            flag=wx.EXPAND,
            border=10)

        # add submit button to main box sizer
        szrMain.Add(
            self.btnSubmit,
            proportion=0,
            flag=wx.EXPAND,
            border=10)

        self.SetSizer(szrMain)
        self.Layout()

        # update available ports combo box
        self.OnRefreshPorts(event=None)
        self.restorePortSelection(portString=self.defaultPort)

        # open connection to target if some port has been selected
        self.OnPortChanged(None)

        # pre-select defaultBaudrate of the baudrate combo box by it's index
        self.cmbBaudRate.SetSelection(self.defaultBaudrateIndex)

        # auto connect to target
        self.OnConnectTarget(None)

    def __create_menu(self):
        MenuBar = wx.MenuBar()

        # general file menu
        FileMenu = wx.Menu()
        item = FileMenu.Append(
            wx.ID_EXIT,
            "&Quit")
        self.Bind(wx.EVT_MENU, self.OnClose, item)

        FileMenu.AppendSeparator()
        item = FileMenu.Append(
            wx.ID_ANY,
            "&Quit\tCtrl-Q",
            "&Quit")
        self.Bind(wx.EVT_MENU, self.OnClose, item)

        # help menu
        HelpMenu = wx.Menu()
        # this gets put in the App menu on OS-X
        item = HelpMenu.Append(
            wx.ID_ABOUT,
            "&About EVSE Serial Debug Monitor")
        self.Bind(
            wx.EVT_MENU,
            self.OnAbout,
            item)
        MenuBar.Append(HelpMenu, "&Help")

        self.SetMenuBar(MenuBar)

    ##
    ## @brief      Stop all active tasks
    ##
    ## @param      self  The object
    ##
    ## @return     None
    ##
    def stopAllTasks(self):
        try:
            # stop all timer here
            self.redrawTimer.Stop()
            self.comTimer.Stop()

            self.stopReceivingThread()

            self.logger.debug("all tasks are stopped")
        except Exception as e:
            self.logger.warning(e)

    ##
    ## @brief      Read the USB port in an endless loop
    ##
    ## @param      self     The object
    ## @param      running  Bool to stay in the while loop
    ##
    ## @return     None
    ##
    def read(self, running, connection):
        self._runReadThread = running

        self.logger.debug("Serial Read Thread started")

        if not connection:
            self.logger.error("No Serial connection given")
            return
        else:
            if not connection.isOpen():
                self.logger.warning("Connection not yet active")
                connection.open()
            else:
                pass

        # create endless reading loop in a seperate thread.
        # kill it by calling stopReadingThread()

        # change this variable to stop this thread
        # https://stackoverflow.com/questions/18018033/how-to-stop-a-looping-thread-in-python
        while self._runReadThread:
            if connection and connection.isOpen():
                # for PySerial v3.0 or later, use property "in_waiting"
                # instead of function inWaiting()
                # https://stackoverflow.com/questions/17553543/pyserial-non-blocking-read-loop

                unixMicros = self.getCurrentTime()
                # unixMicros = self.getUnixMicrosTimestamp()
                line = ""

                # if incoming bytes are waiting to be read from serial input
                # buffer
                if (connection.inWaiting() > 0):
                    # read a '\n' terminated line
                    line = connection.readline()

                # if read thing is not empty
                if line != "":
                    self.logger.debug("Read line: %s" %(line))

                    # create dict of this message
                    messageDict = dict()
                    messageDict["timestamp"] = unixMicros
                    messageDict["message"] = line

                    # add this message dict to the received queue
                    # self._recievedQueue.put(messageDict)

                    # AppendText is not thread safe!
                    # self.txtSerialMonitor.AppendText(line)
                    self.listen_event(data=messageDict)
                    self.listen_json_event(data=line)

                time.sleep(0.1)

    """
    def getReceiveQueue(self):
        return self._recievedQueue
    """

    ##
    ## @brief      Starts the receiving thread.
    ##
    ## @param      self  The object
    ##
    ## @return     None
    ##
    def startReceivingThread(self):
        self.pauseReceivingThread(pause=False)
        self._receivingThread = threading.Thread(
            target=self.read,
            args=(True, self._conn),
            # daemon=True,
            name="ReadingThread")
        self._receivingThread.start()

    ##
    ## @brief      Pause receiving thread
    ##
    ## @param      self   The object
    ## @param      pause  The pause
    ##
    ## @return     None
    ##
    def pauseReceivingThread(self, pause=False):
        self.logger.info("Pausing receiving thread: %s" %(pause))
        self._runReadThread = not pause

    ##
    ## @brief      Stop the receiving thread
    ##
    ## @param      self  The object
    ##
    ## @return     None
    ##
    def stopReceivingThread(self):
        self.logger.info("Stopping receiving thread now")
        self._runReadThread = False

        # wait up to 1 second until thread terminates
        self._receivingThread.join(1)

        if self._receivingThread is not None:
            del self._receivingThread

    ##
    ## @brief      Gets the receiving thread state.
    ##
    ## @param      self  The object
    ##
    ## @retval     True     Running receiving commands from device
    ## @retval     False    Not receiving commands from device
    ##
    def getReceivingThreadState(self):
        return self._runReadThread

    ##
    ## @brief      Gets the unix timestamp in micros.
    ##
    ## @param      self  The object
    ##
    ## @return     The unix timestamp in micros.
    ##
    def getUnixMicrosTimestamp(self):
        # given in seconds, multiply by 1000 to get millis, again times 1000 to get micros
        return int(time.time()*1000*1000)

    ##
    ## @brief      Gets the current time.
    ##
    ## Format is Hour:Minutes:Seconds:Microseconds
    ##
    ## @param      self  The object
    ##
    ## @return     The timestamp as string.
    ##
    def getCurrentTime(self):
        return datetime.datetime.now().strftime("%H:%M:%S:%f")

    ##
    ## @brief      Return runtime of the app
    ##
    ## @param      self  The object
    ##
    ## @return     The runtime
    ##
    def getRuntime(self):
        stopTime = datetime.datetime.now()  # get current time
        theRunTime = stopTime - self.startTime  # time difference aka runtime

        return theRunTime

    ##
    ## @brief      Convert nested dict to flat dict
    ##
    ## @param      self  The object
    ## @param      y     Dict to flatten
    ##
    ## @return     Flat JSON structure
    ##
    def flatten_json(self, y):
        out = {}

        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x

        flatten(y)

        return out

    def getDebugItemDetail(self, key):
        # index of this row
        index = 0

        # remove all elements/rows/items in this list view
        self.item_detail_list.DeleteAllItems()

        # if this element contains a nested dict, make it flat before showing
        if type(self.debugInfoDict[key]) is dict:
            # flatten this element
            flatElement = self.flatten_json(self.debugInfoDict[key])

            # add new rows for all elements of the flat dict
            for el, val in sorted(flatElement.items()):
                # add key (most left column of this list)
                self.item_detail_list.InsertItem(index, el)

                # add value to this key (most right column of this list)
                self.item_detail_list.SetItem(index, 1, str(flatElement[el]))
                index += 1
        else:
            # add key (most left column of this list)
            self.item_detail_list.InsertItem(index, key)

            # add value to this key (most right column of this list)
            self.item_detail_list.SetItem(index, 1, str(self.debugInfoDict[key]))

    def getAllDebugItems(self, data):
        # self.logger.debug("Received: %s, of type %s" %(data, type(data)))

        try:
            self.debugInfoDict = json.loads(data)
            # self.logger.debug(self.debugInfoDict)

            # prettyJsonDump = json.dumps(self.debugInfoDict, indent=4)
            # self.logger.debug(prettyJsonDump)

            # remove all elements/rows/items in this list view
            self.item_list.DeleteAllItems()

            for ele, val in sorted(self.debugInfoDict.items(), reverse=True):
                self.item_list.InsertItem(0, ele)

            # do only if debugInfoDict has content
            if self.debugInfoDict:
                self.restorePreviousSelection()
        except Exception as e:
            pass
            # self.logger.warning(e)

    def restorePreviousSelection(self):
        idx = self.activeUserSelection["item"]
        self.item_list.Focus(idx)
        self.item_list.Select(idx)

        focItm = self.item_list.GetFocusedItem()
        focItmTxt = self.item_list.GetItemText(focItm)

        # load its detail content
        self.getDebugItemDetail(key=focItmTxt)

        # select last selected detail item
        # idx = self.activeUserSelection["detail"]
        # self.item_detail_list.Focus(idx)
        # self.item_detail_list.Select(idx)

    def restorePortSelection(self, portString):
        matchingIndexList = list()

        # search for matching string in available ports, if portString not ""
        if len(portString):
            # search for matches of self.defaultPort in available ports list
            matchingIndexList = [idx for idx, val in enumerate(self.availablePorts) if portString in val]

        # comboBox selection is done by index, -1 is None/empty selection
        matchingIndex = -1

        if len(matchingIndexList):
            # take first match if list contains at least 1 element
            matchingIndex = matchingIndexList[0]
        else:
            pass
            # specify explicit value or use wx constant
            # matchingIndex = wx.NOT_FOUND

            # self.logger.warning("Specified defaultPort is not available for selection, using None/empty")

        # pre-select the port of the port combo box
        self.cmbPorts.SetSelection(matchingIndex)

    def listen_event(self, data):
        wx.CallAfter(self.fillSerialConsole, data)

    def listen_json_event(self, data):
        wx.CallAfter(self.getAllDebugItems, data)

    def fillSerialConsole(self, data):
        # build message string
        textMessage = "%s \t %s" %(data["timestamp"], data["message"])

        txtContent = self.txtSerialMonitor.GetValue()

        # limit content length to 10000 characters
        newLength = len(txtContent) + len(textMessage)
        if newLength > self.maxSerialChars:
            newLength = self.maxSerialChars - len(textMessage)

            # set new content to last N characters
            self.txtSerialMonitor.SetValue(txtContent[-newLength:])

        # append text after cutting the existing text, to automatically scroll
        # to bottom position
        self.txtSerialMonitor.AppendText(textMessage)

    def OnPortChanged(self, event):
        if self.cmbPorts.GetCurrentSelection() < 0:
            # no port has been selected yet
            return

        try:
            self.txtSerialMonitor.AppendText('** Opening Serial Port\n')

            thisBaudrate = self.cmbBaudRate.GetString(self.cmbBaudRate.GetCurrentSelection())
            thisPort =  self.cmbPorts.GetString(self.cmbPorts.GetCurrentSelection())

            self._conn = serial.Serial(
                port=thisPort,
                baudrate=int(thisBaudrate),
                # parity=serial.PARITY_ODD,
                # stopbits=serial.STOPBITS_TWO,
                # bytesize=serial.SEVENBITS,
                timeout=0.4,  # IMPORTANT, can be lower or higher
                # inter_byte_timeout=0.1  # Alternative
            )
            self._conn.close()

            self.txtSerialMonitor.AppendText('** Baud Rate: %s \n' %(thisBaudrate))
        except serial.serialutil.SerialException as e:
            self.txtSerialMonitor.AppendText('** An Error Occurred while Opening the Serial Port\n')
            self.logger.warning("Error: ", e)

    def OnBaudRateChanged(self, event):
        cmbBox = self.cmbPorts
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, cmbBox.GetId())
        wx.PostEvent(cmbBox, evt)
        # event.Skip()

    def OnRefreshPorts(self, event):
        lastString = self.cmbPorts.GetStringSelection()

        ports = list(port_list.comports())
        self.cmbPorts.Clear()
        self.availablePorts = list()

        for p in ports:
            self.cmbPorts.Append(p.device)
            self.availablePorts.append(p.device)

        # try to restore previously selected port
        self.restorePortSelection(portString=lastString)

    def OnConnectTarget(self, event):
        if self._conn.isOpen():
            # connection is open
            self.logger.debug("Port is open, closing now")

            self._conn.close()

            if self._receivingThread != None:
                # stop any (may already running) receiving thread
                self.stopReceivingThread()

            self.btnConnect.SetLabel("Connect")
            self.logger.debug("Port is closed, ready to open")
        else:
            # connection not yet open
            self.logger.debug("Port is not open, opening now")

            self._conn.open()

            time.sleep(0.1)

            # start the receiving thread
            self.startReceivingThread()

            self.btnConnect.SetLabel("Disconnect")
            self.logger.debug("Port is open now, ready to receive")

    def OnKey(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN:
            button = self.btnSubmit
            evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, button.GetId())
            wx.PostEvent(button, evt)
        else:
            event.Skip()

    def OnSubmit(self, event):
        if self.txtSubmitString.GetValue() == 'exit':
            if(self._conn != None and self._conn.isOpen()):
                self._conn.close()
            exit()

        if(self._conn != None):
            if self.txtSubmitString.GetValue() == 'exit':
                self._conn.close()
                exit()
            else:
                strOut = self.txtSubmitString.GetValue() + b'\r\n'
                self.txtSerialMonitor.AppendText("\r\n>> " + self.txtSubmitString.GetValue())
                self._conn.write(strOut.encode())
                out = ''
                # let's wait one second before reading output (let's give device time to answer)
                time.sleep(1)
                while self._conn.inWaiting() > 0:
                    out += self._conn.read(1)

                if out != '':
                    self.txtSerialMonitor.AppendText(out)

        self.txtSubmitString.Clear()

    def OnPaint(self, evt):
        width, height = self.item_detail_list.GetSize()
        for i in range(2):
            self.item_detail_list.SetColumnWidth(i, width/2)
        evt.Skip()

    def OnDebugItemSelected(self, event):
        # called as a element of the source is selected
        item = event.GetText().replace(" ", "-")
        itemIdx = event.GetIndex()

        # self.logger.debug("user selected item: %s, idx %d" %(item, itemIdx))
        self.activeUserSelection["item"] = itemIdx
        self.activeUserSelection["detail"] = 0

        self.getDebugItemDetail(key=item)

    def OnDetailSelected(self, event):
        # called as a element of the detail view is selected
        item = event.GetText()
        itemIdx = event.GetIndex()

        # self.logger.debug("user selected item detail: %s, idx %d" %(item, itemIdx))
        self.activeUserSelection["detail"] = itemIdx

    ##
    ## Called on about.
    ##
    ## open an about window, containing infos about the app, licensing,
    ## the developer and the homepage
    ##
    ## :param      event:  The event
    ## :type       event:  WX EVENT
    ##
    def OnAbout(self, event):
        logger = logging.getLogger(__name__)

        aboutInfo = wx.adv.AboutDialogInfo()
        aboutInfo.SetName("EVSE Serial Debug Monitor")
        aboutInfo.SetVersion("0.2.0")
        aboutInfo.SetDescription(("Serial Monitor with JSON parser for EVSE Debug output"))
        aboutInfo.SetCopyright("(C) 2020")
        licenseText = open("LICENSE", 'r').read()
        aboutInfo.SetLicense(licenseText)
        aboutInfo.SetWebSite("http://github.com/brainelectronics", "EVSE Debug Monitor")
        aboutInfo.AddDeveloper("brainelectronics")

        wx.adv.AboutBox(aboutInfo)

    ##
    ## @brief      Quit app and stop all tasks
    ##
    ## @param      self   The object
    ## @param      event  The event
    ##
    ## @return     None
    ##
    def OnClose(self, event):
        logger = logging.getLogger(__name__)

        self.stopAllTasks()

        if self._conn and self._conn.isOpen():
            self._conn.close()
            self.logger.debug("Closed serial connection")

        logger.info("... closing app after %s" %self.getRuntime())

        self.Destroy()

# end of class frmSerialMonitor

class MyApp(wx.App):
    def OnInit(self):
        self.frameSerialMonitor = frmSerialMonitor(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frameSerialMonitor)
        self.frameSerialMonitor.Show()
        return True

# end of class MyApp

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()
