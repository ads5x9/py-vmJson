import jsonpickle

# In order for jsonpickle to work correctly, we need a class that contains all the data we want to pickle in it.
# In this particular scnerio, we're gonna have lists of classes, so I'll make multiple classes.

# This class represents a single virtual hard disk.
class singleDisk():
    def __init__(self, label, cap, thinProv, fileLoc):
        self.label = label
        self.capacity = cap
        self.thinProv = thinProv
        self.fileLocation = fileLoc

# This class represents a single virtual NIC.
class singleNic():
    def __init__(self, label, MAC, summary=None):
        self.label = label
        self.mac = MAC
        # Summary is optional.
        if not summary == None:
            self.summary = summary

## This class represents CPU statistics for a single host.
class cpuStats():
    def __init__(self, coreCount, utilizationPerc):
        self.cores = coreCount
        self.util = utilizationPerc

# This class represents RAM stats for a single host.
class ramStats():
    def __init__(self, total, shared, balloon, swap, active):
        self.total = total
        self.shared, self.balloon, self.swap, self.active = shared, balloon, swap, active

# This class represents a single virtual machine.
# Its made up of several of the previous classes.
class singleVM():
    def __init__(self, name, guest):
        self.diskList = []
        self.nicList = []
        self.cpu = object
        self.ram = object
        self.name, self.guest = name, guest
    #def addDisk(self, label, cap, thinProv, fileLoc):
    #    newDisk = singleDisk(label, cap, thinProv, fileLoc)
    #    self.diskList.append(newDisk)
    def addDisk(self, diskObj):
        self.diskList.append(diskObj)
    #def addNic(self, label, MAC, summary=None):
    #    newNic = singleNic(label, MAC, summary)
    #    self.nicList.append(newNic)
    def addNic(self, nicObj):
        self.nicList.append(nicObj)
    def setCPU(self, coreCount, utilPerc):
        newCPU = cpuStats(coreCount, utilPerc)
        self.cpu = newCPU
    def setRAM(self, total, shared, balloon, swap, active):
        newRAM = ramStats(total, shared, balloon, swap, active)
        self.ram = newRAM

# This class represents a single datastore.
class singleDatastore():
    def __init__(self, name, capacity, freeSpace):
        self.name, self.cap, self.freeSpace = name, capacity, freeSpace
	#self.freePercent = 100 - ((freeSpace / capacity) * 100)
	self.usedPercent = ((capacity - freeSpace) / float(capacity)) * 100

# This class represents a single host, on which VMs run.
class singleHost():
    def __init__(self, name, cpuType):
        self.name, self.cpuType = name, cpuType
        self.VMs = []
    def addVm(self, vmName):
        self.VMs.append(vmName)

# This class encapsulates all previous classes in this file.
# It represents the one-line JSON string that this program generates.
class vmwareReport():
    def __init__(self):
	import datetime
        self.reportTime = str(datetime.datetime.now())
        self.vmList = []
        self.datastoreList = []
        self.hostList = []
    # we use diskCount and nicCount to specify how many disks and nics there are, so we can properly index the lists.
    #def addVM(self, name, guest, diskCount, nicCount, diskLabel, diskCap, diskThinProv, diskFileLoc, nicLabel, nicMAC, nicSum, cpuCores, cpuPerc, ramTot, ramShared, ramBalloon, ramSwap, ramActive):
    #    vm = singleVM(name, guest)
    #    for i in xrange(diskCount):
    #        vm.addDisk(diskLabel[i], diskCap[i], diskThinProv[i], diskFileLoc[i])
    #    for i in xrange(nicCount):
    #        vm.addNic(nicLabel[i], nicMAC[i], nicSum[i])
    #    vm.setCPU(cpuCores, cpuPerc)
    #    vm.setRAM(ramTot, ramShared, ramBalloon, ramSwap, ramActive)
    #    self.vmList.append(vm)
    def addVM(self, name, guest, diskObj, nicObj, cpuCores, cpuPerc, ramTot, ramShared, ramBalloon, ramSwap, ramActive):
        vm = singleVM(name, guest)
        for disk in diskObj:
            vm.addDisk(disk)
        #vm.addDisk(diskObj)
        #vm.addNic(nicObj)
        for nic in nicObj:
            vm.addNic(nic)
        vm.setCPU(cpuCores, cpuPerc)
        vm.setRAM(ramTot, ramShared, ramBalloon, ramSwap, ramActive)
        self.vmList.append(vm)
    #def addVM(self, newVMObj):
    #    self.vmList.append(newVMObj)
    def addDatastore(self, name, capacity, freeSpace):
        # First, make sure the datastore isn't already present.
        for datastore in self.datastoreList:
            if name == datastore.name:
                return
        ds = singleDatastore(name, capacity, freeSpace)
        self.datastoreList.append(ds)
    def addHost(self, name, cpuType):
        # First, make sure the host isn't already present.
        for host in self.hostList:
            if name == host.name:
                return
        host = singleHost(name, cpuType)
        self.hostList.append(host)
    def addVMToHost(self, hostName, vmName):
        for host in self.hostList:
            if host.name == hostName:
                for vm in host.VMs:
                    if vm == vmName:
                        return        # Already added
                host.addVm(vmName)
                return
        # If we made it here, something broke.
        raise RuntimeError("{} was not in host list.".format(hostName))

# Now that the classes are defined, we can create our json pickle.
def jsonPickleReport(report, localdebug=False):
    retu = jsonpickle.encode(report)
    if localdebug: print("jsonPickleReport: {}".format(retu))
    return retu
