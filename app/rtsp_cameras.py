import sys
import socket
from datetime import datetime
from os import getenv,environ
from portscan import PortScan
import subprocess
import requests
import json
class RTSPCameras:
    def __init__(self,verbose=False,enable=False,addcameras=False,delcameras=False,wspace=""):
        # GET ENVIRONMENT VARIABLES
        RTSP_WHITESPACE = getenv("RTSP_WHITESPACE","-")
        RTSP_CAMERAS_ENABLE = getenv("RTSP_CAMERAS_ENABLE","false")
        RTSP_CAMERAS_ADD = getenv("RTSP_CAMERAS_ADD","false")
        RTSP_CAMERAS_DEL = getenv("RTSP_CAMERAS_DEL","false")
        RTSP_VERBOSE = getenv("RTSP_VERBOSE","false")
        RTSP_ADDRESS = getenv("RTSP_ADDRESS","192.168.2.0/24")
        RTSP_HOSTS = getenv("RTSP_HOSTS",None)
        RTSP_PORTS = getenv("RTSP_SCAN_PORTS","554,8554")
        RTSP_CREDS = self.splitEnvCSV(getenv("RTSP_CREDS","none"))
        RTSP_PATHS = self.splitEnvCSV(getenv("RTSP_PATHS","/Streaming/Channels/101,/live"))
        self.enable = True if RTSP_CAMERAS_ENABLE.lower() == "true" or enable == True else False
        self.addcameras = True if RTSP_CAMERAS_ADD.lower() == "true" or addcameras == True else False
        self.delcameras = True if RTSP_CAMERAS_DEL.lower() == "true" or delcameras == True else False
        self.verbose = True if verbose or str(RTSP_VERBOSE).lower() == "true" else False
        self.whitespace = RTSP_WHITESPACE if RTSP_WHITESPACE  else wspace
        
        self.creds = RTSP_CREDS
        self.paths = RTSP_PATHS
        if RTSP_PORTS:
            self.ports = RTSP_PORTS
        if RTSP_HOSTS:
            # Takes priority over RTSP_ADDRESS.  If set, self.address is set to False
            self.address=False
            # Split RTSP_HOSTS into a list called self.hosts
            self.hosts = RTSP_HOSTS.split(",")
        else:
            self.hosts = False
            if RTSP_ADDRESS:
                self.address = RTSP_ADDRESS
            else:
                self.address = "192.168.1.0/24"
        self.cameras = []
            
    def run(self):
        if self.enable:
            if self.addcameras and self.delcameras:
                errormsg =  "Did you really want to add and delete the same cameras?\n\n"
                errormsg += "'Listen, three eyes,' he said, 'don't you try to outweird me, I get stranger"
                errormsg += " things than you free with my breakfast cereal.'"
                print(errormsg)
                return
            else:
                self.scanner()
                if self.delcameras:
                    self.delCameras()
                elif self.addcameras:
                    if self.verbose:
                        print(self.cameras)
                        print(self.creds)
                        print(self.paths)
                        print(self.address)
                        print(self.ports)
                    self.addCameras()
                else:
                    for c in range(0,len(self.cameras)):
                        self.cameras[c][0] = self.cameras[c][0].replace('.',self.whitespace)
        else:
            print("Scanning Disabled")
            
        if not self.addcameras:
            return self.cameras
            
    def splitEnvCSV(self,csv):
        values = []
        for value in csv.split(','):
            values.append(value)
        return values
    
    def scanner(self):
        if self.hosts:
            results = []
            for host in self.hosts:
                self.portscan = PortScan(host,self.ports,stdout=False)
                result = self.portscan.run()
                for item in result:
                    if item:
                        results.append(item)
        else:
            self.portscan = PortScan(self.address,self.ports,stdout=False)
            results = self.portscan.run()
            with self.portscan.q.mutex:
                unfinished = self.portscan.q.unfinished_tasks - len(self.portscan.q.queue)
                if unfinished <= 0:
                    if unfinished < 0:
                        raise ValueError('task_done() called too many times')
                    self.portscan.q.unfinished_tasks = unfinished
                    self.portscan.q.queue.clear()
                    self.portscan.q.not_full.notify_all()
        if self.verbose:
            print(results)
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
                            status += "RTSP"
                        if self.verbose:
                            print(status)
    def delCameras(self):
        for cam in range(0,len(self.cameras)):
            self.cameras[cam][0] = self.cameras[cam][0].replace(".",self.whitespace).replace(" ","_")
            apiURL = f'http://192.168.2.240:9997/v1/config/paths/remove/{self.cameras[cam][0]}'
            outputString = f"Deleting {self.cameras[cam][0]} - {self.cameras[cam][1]} | "
            response = requests.post(apiURL)
            outputCode = f"{response.status_code} : "
            if response.status_code == 200:
                outputResult = "SUCCESS"
            else:
                outputResult = "FAILURE"
            print(f"{outputString}{outputCode}{outputResult}")
            
    def addCameras(self):
        for cam in range(0,len(self.cameras)):
            jsonPostData =  {
                            "source": self.cameras[cam][1],
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
            self.cameras[cam][0] = self.cameras[cam][0].replace(".",self.whitespace).replace(" ","_")
            outputString = f"Adding {self.cameras[cam][0]} - {self.cameras[cam][1]} | "
            outputCode = ""
            outputResult = ""
            apiURL = f'http://192.168.2.240:9997/v1/config/paths/add/{self.cameras[cam][0]}'
            if self.addcameras:
                response = requests.post(apiURL,json=jsonPostData)
                outputCode = f"{response.status_code} : "
                if response.status_code == 200:
                    outputResult = "SUCCESS"
                else:
                    outputResult = "FAILURE"
            else:
                outputResult = "DISABLED"
            print(f"{outputString}{outputCode}{outputResult}")
            if self.verbose and outputResult != "SUCCESS":
                print(json.dumps(jsonPostData,ensure_ascii=True))