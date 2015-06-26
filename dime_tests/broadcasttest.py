from pymatbridge import Matlab

#start two matlab instances
print "Starting"
mlab1 = Matlab()
#mlab2 = Matlab()
mlab1.start()
#mlab2.start()

print "Adding setting path = p"
mlab1.run_code("p = genpath('/Users/austinmcever/Documents/Sum15Research/dime2/')")
print "Adding path"
mlab1.run_code("addpath(p)")
#print "Starting Instance1"
#mlab1.run_code("dime.start('Instance1')")
#print "Instance1 connected"

#mlab2.run_code("addpath(genpath('/Users/austinmcever/Documents/Sum15Research/dime2/'))")
#mlab2.run_code("dime.start('Instance2')")
#print "Instance2 connected"

#create and send testvar
mlab1.run_code("testvar = 5")
print "Testvar created"
#mlab1.run_code("dime.broadcast('testvar')")

#recieve testvar and check
#mlab2.run_code("dime.sync()")
testvar = mlab1.get_variable("testvar")

print "testvar = {}".format(testvar)