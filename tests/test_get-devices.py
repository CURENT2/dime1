import matlab.engine

m1 = matlab.engine.start_matlab()
m2 = matlab.engine.start_matlab()

#insert your path to dime here...
#make this an argument? find using sys library?
dimepath = '/Users/austinmcever/Documents/Sum15Research/dime2'

gendpath = m1.genpath(dimepath)

m1.addpath(gendpath)
m2.addpath(gendpath)

m1.dime.start('m1', nargout=0)
m2.dime.start('m2', nargout=0)

devicedict = m1.dime.get_devices()

users = devicedict['response']

if 'm1' in users and 'm2' in users:
     print "Success"
else:
    print "Failure"

m1.dime.exit(nargout=0)
m2.dime.exit(nargout=0)
m1.quit()
m2.quit()
