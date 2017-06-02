#!/usr/bin/env python
from __future__ import print_function
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim
from datetime import timedelta, datetime

import argparse
import atexit
import getpass
import ssl

import jsonPickle                    # This is a local file. It contains our homemade classes and the pickle method.

hostdict = {}
datastoredict = {}

# This function was copied from example code. It uses argparse to parse command line arguments.
def GetArgs():
    parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store', help='Password to use when connecting to host')
    parser.add_argument('-m', '--vm', required=True, action='store', help='Comma seperated list of Virtual Machines to report on')
    parser.add_argument('-c', '--cert_check_skip', required=False, action='store_true', help='skip ssl certificate check')
    parser.add_argument('-i', '--interval', type=int, default=15, action='store', help='Interval to average the vSphere stats over')
    parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode, produce extra output")
    args = parser.parse_args()
    return args

# This function was copied from example code. It reaches out to the ESXi host we've connected to,
# and queries it for "live," dynamic information - information that changes over time, such as
# memory utilization, CPU utilization, and the like.
def BuildQuery(content, vchtime, counterId, instance, vm, interval):
    #print("\tBuildQuery: {}".format(counterId))
    perfManager = content.perfManager
    metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance=instance)
    startTime = vchtime - timedelta(minutes=(interval + 1))
    endTime = vchtime - timedelta(minutes=1)
    query = vim.PerformanceManager.QuerySpec(intervalId=20, entity=vm, metricId=[metricId], startTime=startTime, endTime=endTime)
    perfResults = perfManager.QueryPerf(querySpec=[query])
    if perfResults:
        return perfResults
    else:
        print('ERROR: Performance results empty.  TIP: Check time drift on source and vCenter server')
        print('Troubleshooting info:')
        print('vCenter/host date and time: {}'.format(vchtime))
        print('Start perf counter time   :  {}'.format(startTime))
        print('End perf counter time     :  {}'.format(endTime))
        print(query)

# This function was copied from example code.
# It returns the value from a specified dictionary's key.
# We use it to get the int id of a performance counter.
def StatCheck(perf_dict, counter_name):
    counter_key = perf_dict[counter_name]
    return counter_key
    
    
# This function was copied from example code. It retrieves the properties
# that describe the virtual machines in our environment. 
def GetProperties(content, viewType, props, specType):
    # Build a view and get basic properties for all Virtual Machines
    objView = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)
    tSpec = vim.PropertyCollector.TraversalSpec(name='tSpecName', path='view', skip=False, type=vim.view.ContainerView)
    pSpec = vim.PropertyCollector.PropertySpec(all=False, pathSet=props, type=specType)
    oSpec = vim.PropertyCollector.ObjectSpec(obj=objView, selectSet=[tSpec], skip=False)
    pfSpec = vim.PropertyCollector.FilterSpec(objectSet=[oSpec], propSet=[pSpec], reportMissingObjectsInResults=False)
    retOptions = vim.PropertyCollector.RetrieveOptions()
    totalProps = []
    retProps = content.propertyCollector.RetrievePropertiesEx(specSet=[pfSpec], options=retOptions)
    totalProps += retProps.objects
    while retProps.token:
        retProps = content.propertyCollector.ContinueRetrievePropertiesEx(token=retProps.token)
        totalProps += retProps.objects
    objView.Destroy()
    # Turn the output in retProps into a usable dictionary of values
    gpOutput = []
    for eachProp in totalProps:
        propDic = {}
        for prop in eachProp.propSet:
            propDic[prop.name] = prop.val
        propDic['moref'] = eachProp.obj
        gpOutput.append(propDic)
    return gpOutput



# This function will establish a single VM's information. 
# The host its on will be added to the global host dictionary. 
# The datastores it uses will be added to the global datastore dict.
# The VM object will be returned to the calling function.
def processVM(myVm, reportObj, content, vchtime, interval, perfDict):
    # At the end of this function, we'll call addVM(). We need to get all that function's info available. 
    global hostdict
    global datastoredict
    statInt = interval * 3  # There are 3 20s samples in each minute
    diskList = []
    nicList = []
    vmName = myVm.config.name
    vmGuest = myVm.summary.guest.guestFullName
    cpuCount = myVm.summary.config.numCpu
    totalRAM = myVm.summary.config.memorySizeMB
    #vmObj = jsonPickle.singleVM(vmName, vmGuest)
    
    # Convert limit and reservation values from -1 to None - copied from example code.
    #if myVm.resourceConfig.cpuAllocation.limit == -1:
    #    vmcpulimit = "None"
    #else:
    #    vmcpulimit = "{} Mhz".format(myVm.resourceConfig.cpuAllocation.limit)
    #if myVm.resourceConfig.memoryAllocation.limit == -1:
    #    vmmemlimit = "None"
    #else:
    #    vmmemlimit = "{} MB".format(myVm.resourceConfig.cpuAllocation.limit)
    #if myVm.resourceConfig.cpuAllocation.reservation == 0:
    #    vmcpures = "None"
    #else:
    #    vmcpures = "{} Mhz".format(myVm.resourceConfig.cpuAllocation.reservation)
    #if myVm.resourceConfig.memoryAllocation.reservation == 0:
    #    vmmemres = "None"
    #else:
    #    vmmemres = "{} MB".format(myVm.resourceConfig.memoryAllocation.reservation)
    
    # Virtual disks have a key value between 2,000 and 3,000. NICs are between 4,000 and 5,000
    # Gather vdisks and vnics by iterating through every vdevice
    for virtualDevice in myVm.config.hardware.device:
        if virtualDevice.key >= 2000 and virtualDevice.key < 3000:
            newDisk = jsonPickle.singleDisk(virtualDevice.deviceInfo.label, virtualDevice.capacityInKB, virtualDevice.backing.thinProvisioned, virtualDevice.backing.fileName)
            diskList.append(newDisk)
        elif virtualDevice.key >= 4000 and virtualDevice.key < 5000:
            newNic = jsonPickle.singleNic(virtualDevice.deviceInfo.label, virtualDevice.macAddress, virtualDevice.deviceInfo.summary)
            nicList.append(newNic)
    # Because of the nature of the API, we have to reach out to the host to query the
    # cpu and memory information. They aren't provided in the myVM object because they're
    # constantly changing. 
    # We'll copy this from the example code.
    statCpuUsage = BuildQuery(content, vchtime, (StatCheck(perfDict, 'cpu.usage.average')), "", myVm, interval)
    cpuUsage = ((float(sum(statCpuUsage[0].value[0].value)) / statInt) / 100)
    #Memory Active Average over Interval in MB
    statMemoryActive = BuildQuery(content, vchtime, (StatCheck(perfDict, 'mem.active.average')), "", myVm, interval)
    activeRAM = (float(sum(statMemoryActive[0].value[0].value) / 1024) / statInt)
    #Memory Shared
    statMemoryShared = BuildQuery(content, vchtime, (StatCheck(perfDict, 'mem.shared.average')), "", myVm, interval)
    sharedRAM = (float(sum(statMemoryShared[0].value[0].value) / 1024) / statInt)
    #Memory Balloon
    statMemoryBalloon = BuildQuery(content, vchtime, (StatCheck(perfDict, 'mem.vmmemctl.average')), "", myVm, interval)
    balloonRAM = (float(sum(statMemoryBalloon[0].value[0].value) / 1024) / statInt)
    #Memory Swapped
    statMemorySwapped = BuildQuery(content, vchtime, (StatCheck(perfDict, 'mem.swapped.average')), "", myVm, interval)
    swappedRAM = (float(sum(statMemorySwapped[0].value[0].value) / 1024) / statInt)
    
    # Add this VM to the report.
    reportObj.addVM(vmName, vmGuest, diskList, nicList, cpuCount, cpuUsage, totalRAM, sharedRAM, balloonRAM, swappedRAM, activeRAM)
    
    # Add datastore(s) to the report.
    for store in myVm.datastore:
        dsName = store.name
        dsCapacity = store.summary.capacity
        dsFree = store.summary.freeSpace
        reportObj.addDatastore(dsName, dsCapacity, dsFree)
        
    # Add host to the report.
    reportObj.addHost(myVm.summary.runtime.host.name, vmName)
    reportObj.addVMToHost(myVm.summary.runtime.host.name, vmName)
# End processVM


def main():
    global hostdict
    global datastoredict
    args = GetArgs()
    vmnames = args.vm
    try:
        si = None
        if args.password:
            password = args.password
        else:
            password = getpass.getpass(prompt="Enter password for host {} and user {}: ".format(args.host, args.user))
        # Attempt connection to vmware host
        try:
            if args.cert_check_skip:
                context = ssl._create_unverified_context()
                si = SmartConnect(host=args.host, user=args.user, pwd=password, port=int(args.port), sslContext=context)
            else:
                si = SmartConnect(host=args.host, user=args.user, pwd=password, port=int(args.port))
        except IOError as e:
            pass
        if not si:
            print('Could not connect to the specified host using specified username and password')
            return -1
        # We are connected, let's work some magic.
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        # Get vCenter date and time for use as baseline when querying for counters
        vchtime = si.CurrentTime()
        
        # Get all the performance counters
        perfDict = {}
        perfList = content.perfManager.perfCounter
        for counter in perfList:
            counter_full = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
            perfDict[counter_full] = counter.key
        
        retProps = GetProperties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)
        
        # thisReport is the object that we will pickle in the near future. It represents a report.
        thisReport = jsonPickle.vmwareReport()
        
        # For each VM, add the VM and its associated info to the VM report.
        for vm in retProps:
            if (vm['name'] in vmnames):     # pass in vm['moref'] so i dont have to keep tying it when i write the function
                processVM(vm['moref'], thisReport, content, vchtime, args.interval, perfDict)
                
        jsonString = jsonPickle.jsonPickleReport(thisReport, args.debug)
        print(jsonString)
                
                
    except vmodl.MethodFault as e:
        print('Caught vmodl fault : ' + e.msg)
        print(e)
        return -1
    except Exception as e:
        print('Caught exception : ' + str(e))
        print(e)
        return -1
    
    return 0
    
if __name__ == "__main__":
    main()
