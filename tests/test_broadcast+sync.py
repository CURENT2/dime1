import matlab.engine

m1 = matlab.engine.start_matlab()
m2 = matlab.engine.start_matlab()

m1.workspace['testvar'] = 10

# insert your path to dime in appropriate dime_class_gen.m
m1.workspace['name'] = 'm1'
m2.workspace['name'] = 'm2'
m1.dime_class_gen(nargout=0)
m2.dime_class_gen(nargout=0)

m1.broadcast_testvar(nargout=0)
m2.sync(nargout=0)

testvar = m2.workspace['testvar']

if testvar == 10:
    print "Variable successfully broadcasted and received"
else:
    print "Test failed"

m1.dexit(nargout=0)
m2.dexit(nargout=0)
m1.quit()
m2.quit()
