import matlab.engine

m1 = matlab.engine.start_matlab()
m2 = matlab.engine.start_matlab()

m1.workspace['testvar'] = 10

dimepath = '/Users/austinmcever/Documents/Sum15Research/dime2'

gendpath = m1.genpath(dimepath)

m1.addpath(gendpath)
m2.addpath(gendpath)

m1.dime.start('m1', nargout=0)
m2.dime.start('m2', nargout=0)

m1.dime.broadcast('testvar', nargout=0)
m2.dime.sync(1, nargout=0)

testvar = m2.workspace['testvar']

if testvar == 10:
    print "Variable successfully broadcasted and received"
else:
    print "Test failed"

m1.dime.exit(nargout=0)
m2.dime.exit(nargout=0)
m1.quit()
m2.quit()
