classdef m3s
    methods(Static)
        
        function [] = exit()
            messenger('exit')
        end
        
        function [] = start(name, address)
            if (nargin < 2)
                address = 'ipc:///tmp/m3c';
            end
            json_startup;
            messenger('init', address);
            messenger('send', name);
            response = messenger('recv')
            % do something
            if strcmp(response, 'DUPLICATE_NAME_ERROR')
                messenger('exit')
                fprintf('Please try again with a different name.\n')
            end
        end

        function [] = sync(max_iterations)
            if (nargin < 1)
                max_iterations = 3;
            end
            counter = max_iterations;
            while(true) 
                outgoing = {};
                % Ask Python if it has anything to send
                outgoing.command = 'sync';
                outgoing.args = '';
                messenger('send', json_dump(outgoing));
                msg = messenger('recv');
                if strcmp(msg, 'COMPLETE')
                    fprintf('Message queue empty. Exiting sync.\n')
                    break;
                end
                if counter <= 0
                    fprintf('Iteration max exceeded. Exiting sync.\n')
                    break;
                end
                % Send the response back as a response command
                rep = pymat_eval(json_load(msg));
                outgoing.command = 'response';
                outgoing.args = rep;
                messenger('send', json_dump(outgoing));
                messenger('recv');
                counter = counter - 1;
            end
        end

        function [] = broadcast(varargin)
            for i = 1:length(varargin)
                var_name = varargin{i};
                outgoing = {};
                outgoing.command = 'broadcast';
                outgoing.args = var_name;
                messenger('send', json_dump(outgoing));
                msg = messenger('recv');

              % eval the code and send the response back
                rep = pymat_eval(json_load(msg))
                outgoing.command = 'response';
                outgoing.args = rep;
                outgoing.meta = struct('var_name', var_name);
                messenger('send', json_dump(outgoing));
                messenger('recv'); % Receive an OK to set state back to "sender"
            end
        end

        function [] = send_var(recipient_name, var_name)
            % Tell Python to pick a variable
            outgoing = {};
            outgoing.command = 'send';
            outgoing.args = var_name;
            messenger('send', json_dump(outgoing));
            msg = messenger('recv');

            % eval the code and send the response back
            rep = pymat_eval(json_load(msg))
            outgoing.command = 'response';
            outgoing.args = rep;
            outgoing.meta = struct('var_name', var_name);
            outgoing.meta.recipient_name = recipient_name;
            messenger('send', json_dump(outgoing));
            messenger('recv'); % Receive an OK to set state back to "sender"
        end

        function rep = get_devices()
            outgoing = {};
            outgoing.command = 'get_devices';
            messenger('send', json_dump(outgoing));
            rep = messenger('recv');
            rep = json_load(rep);
        end
    end
end
