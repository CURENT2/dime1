% This is an example of using DiME in MATLAB

% Construct structures
% The structure 'module_name' is used to pass initialization 
%   needs to the VGS. It has to be consistent with the module name specified in the dime client.
%
% Fields:
%   param: device list to request system parameters in PSAT format
%   vgsvaridx: indicies of the request variables to be streamed at every integration time step 
%              in Varout.vars
%

module_name.vgsvaridx = [ ];

try
    json_startup; % Start JSON
catch
    
end

try
    % Connect as a dime client. Change Module_Name to a unique name;
    % Change the address to your dime server address;
    % If you use tcp, specify the port like 'tcp://127.0.0.1:5000/dime'
    dimec = dime('module_name', 'ipc:///tmp/dime');
    dimec.cleanup();
catch

end

% Start dime connection
dimec.start();
pause(0.1);

% Specify the names of the prerequisit modules
prereqs = {'sim'};
states = zeros(2, length(prereqs));

while(1)

    dev_list = dimec.get_devices.response;

    for item = 1:length(prereqs)
    % Check if the prerequisite modules connect
        if sum(strcmp(dev_list, prereqs(item))) > 0
            states(1, item) = states(2, item);
            states(2, item) = 1;
        end
    end

    if sum(states(2, :)) == length(prereqs) && ...
        sum(states(1, :)) == 0
        % Send initialization info from here
        % For example, to request for system parameters,
        %   Construct a matrix module_name.param = {'component names'}
        %   and send it back to VGS module named 'sim'
        dimec.send_var('sim', module_name);
        disp(' * Debug: Init var send');
        while ~exist('SysParam')
            pause(0.05);
            dimec.sync;
        end
        disp(' Debug: SysParam received');
    end
    
    if sum(states(2, :)) == 0 && sum(states(1, :) == length(prereqs)
        %do some cleanup and reset your module
    end

    if sum(sum(states)) == 2*length(prereqs) || dimec.sync
        % Execute your own code here
    end

end

