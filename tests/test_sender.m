function [] = test_sender()
    addpath(genpath('/home/mohammad/playground/dime'));
    dime.start('test1');
    A = rand(30);
    dime.broadcast('A');
    dime.exit();
    exit
end
