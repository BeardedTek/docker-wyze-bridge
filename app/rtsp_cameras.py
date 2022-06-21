import sys
import socket
from datetime import datetime
from os import getenv
from portscan import PortScan
import subprocess
import requests
import json
class AddRTSPCameras:
    def __init__(self,verbose=False,enable=False):
        
        # GET ENVIRONMENT VARIABLES
        RTSP_ADD_CAMERAS = getenv("RTSP_ADD_CAMERAS","false")
        RTSP_VERBOSE = getenv("RTSP_VERBOSE","false")
        RTSP_ADDRESS = getenv("RTSP_SCAN_NETWORK","192.168.2.0/24")
        RTSP_PORTS = getenv("RTSP_SCAN_PORTS","554,8554")
        RTSP_CREDS = self.splitEnvCSV(getenv("RTSP_CREDS","admin:admin,none"))
        RTSP_PATHS = self.splitEnvCSV(getenv("RTSP_PATHS","/Streaming/Channels/101,/live"))
        
        self.enable = True if RTSP_ADD_CAMERAS.lower() == "true" or enable == True else False
        self.verbose = True if verbose or str(RTSP_VERBOSE).lower() == "true" else False

        self.creds = RTSP_CREDS
        self.paths = RTSP_PATHS
        if self.enable:
            if RTSP_PORTS:
                self.ports = RTSP_PORTS
            if RTSP_ADDRESS:
                self.address = RTSP_ADDRESS
            else:
                self.address = "192.168.1.0"
            self.cameras = []
            self.scanner()
            if self.verbose:
                print(self.cameras)
                print(self.creds)
                print(self.paths)
                print(self.address)
                print(self.ports)
            self.addCameras()
        else:
            print("Scanning Disabled")
    
    def splitEnvCSV(self,csv):
        values = []
        for value in csv.split(','):
            values.append(value)
        return values
    
    def scanner(self):
        scan = PortScan(self.address,self.ports,stdout=False)
        results = scan.run()
        for result in results:
            if result:
                for path in self.paths:
                    for cred in self.creds:
                        if cred == "none":
                            cred = False
                        transport = "rtsp://"
                        if cred:
                            transport += f"{cred}@"
                        rtsp = f'{transport}{result["ip"]}:{result["port"]}{path}'
                        status = f"Checking {rtsp}... "
                        command = ['ffmpeg', '-y', '-frames', '1', 'snapshot.png', '-rtsp_transport', 'tcp', '-i', rtsp]
                        cmd = subprocess.run(command, stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
                        if cmd.returncode == 0:
                            self.cameras.append([str(result['ip']),rtsp])
                            status += "OK"
                        else:
                            status += "KO"
                        if self.verbose:
                            print(status)
                            
    def addCameras(self):
        for camera in self.cameras:
            jsonPostData =  {
                            "source": camera[1],
                            "sourceProtocol": "automatic",
                            "sourceAnyPortEnable": False,
                            "sourceFingerprint": "",
                            "sourceOnDemand": False,
                            "sourceOnDemandStartTimeout": "10s",
                            "sourceOnDemandCloseAfter": "10s",
                            "sourceRedirect": "",
                            "disablePublisherOverride": False,
                            "fallback": "",
                            "publishUser": "",
                            "publishPass": "",
                            "publishIPs": [],
                            "readUser": "",
                            "readPass": "",
                            "readIPs": [],
                            "runOnInit": "",
                            "runOnInitRestart": False,
                            "runOnDemand": "",
                            "runOnDemandRestart": False,
                            "runOnDemandStartTimeout": "10s",
                            "runOnDemandCloseAfter": "10s",
                            "runOnReady": "python3 /app/rtsp_event.py $RTSP_PATH READY",
                            "runOnReadyRestart": False,
                            "runOnRead": "python3 /app/rtsp_event.py $RTSP_PATH READ",
                            "runOnReadRestart": False
                            }
            name = camera[0].replace(".","-")
            apiURL = f'http://192.168.2.240:9997/v1/config/paths/add/{name}'
            response = requests.post(apiURL,json=jsonPostData)
            if response.status_code == 200:
                print(f"Adding {name} - {camera[1]} | {response.status_code} : SUCCESS!")
            else:
                print(f"Adding {name} - {camera[1]} | {response.status_code} : FAILURE!")
                if self.verbose:
                    print(json.dumps(jsonPostData,ensure_ascii=True))