function [] = test_broadcast_speed(path_to_dime)
    addpath(genpath(path_to_dime));
    dime.start('test');
    t = zeros(1, 300);
    global A
    for n = 1:300
        A = rand(n);
        tic;
        dime.broadcast('A');
        t(n) = toc;
    end
    plot(t)
    dime.exit()
end