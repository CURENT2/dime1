classdef dime
    properties
        name; % This client's name
        address;
        listen_to_events;
    end

    methods
        function obj = dime(name, address, listen_to_events)
            if (nargin < 2)
                address = 'ipc:///tmp/dime';
            end

            if (nargin < 3)
                listen_to_events = false;
            end

            obj.name = name;
            obj.address = address;
            obj.listen_to_events = listen_to_events;
        end

        function [] = exit(obj)
            outgoing = {};
            outgoing.command = 'exit';
            outgoing.name = obj.name;

            messenger('send', json_dump(outgoing));
            response = messenger('recv');
            if (strcmp(response, 'OK'))
                messenger('exit');
            end
        end

        function [] = cleanup(obj)
            messenger('exit');
        end

        function [status] = start(obj)
            status = 0;

            messenger('init', obj.address);
            outgoing = {};
            outgoing.command = 'connect';
            outgoing.name = obj.name;
            outgoing.listen_to_events = obj.listen_to_events
            messenger('send', json_dump(outgoing));
            response = messenger('recv');

            if (strcmp(response, 'OK'))
                status = 1;
            end
        end

        function [flag] = sync(obj, max_iterations)
            if (nargin < 2)
                max_iterations = 3;
            end
            counter = max_iterations;
            flag = 1;  % Sync flag
            while(counter)
                outgoing = {};
                % Ask Python if it has anything to send
                outgoing.command = 'sync';
                outgoing.name = obj.name;
                outgoing.args = '';
                messenger('send', json_dump(outgoing));
                msg = messenger('recv');
                if (strcmp(msg, 'OK'))
                    break;
                end

                % Send the response back as a response command
                rep = pymat_eval(json_load(msg));
                outgoing.command = 'response';
                outgoing.name = obj.name;
                outgoing.args = rep;
                messenger('send', json_dump(outgoing));
                messenger('recv');
                counter = counter - 1;
            end

            if counter == max_iterations
                flag = 0;
            end
        end

        function [] = broadcast(obj, varargin)
            for i = 1:length(varargin)
                var_name = varargin{i};
                outgoing = {};
                outgoing.command = 'broadcast';
                outgoing.name = obj.name;
                outgoing.args = var_name;
                messenger('send', json_dump(outgoing));
                msg = messenger('recv')

                % eval the code and send the response back
                rep = pymat_eval(json_load(msg));
                outgoing.command = 'response';
                outgoing.name = obj.name;
                outgoing.args = rep;
                outgoing.meta = struct('var_name', var_name);
                messenger('send', json_dump(outgoing));
                messenger('recv'); % Receive an OK to set state back to "sender"
            end
        end

        function [] = send_var(obj, recipient_name, varargin)
            % Tell Python to pick a variable
            for i = 1:length(varargin)
                var_name = varargin{i};
                outgoing = {};
                outgoing.command = 'send';
                outgoing.name = obj.name;
                outgoing.args = var_name;
                messenger('send', json_dump(outgoing));
                msg = messenger('recv');

                % eval the code and send the response back
                rep = pymat_eval(json_load(msg));
                outgoing.command = 'response';
                outgoing.name = obj.name;
                outgoing.args = rep;
                outgoing.meta = struct('var_name', var_name);
                outgoing.meta.recipient_name = recipient_name;
                messenger('send', json_dump(outgoing));
                messenger('recv'); % Receive an OK to set state back to "sender"
            end
        end

        function rep = get_devices(obj)
            outgoing = {};
            outgoing.command = 'get_devices';
            outgoing.name = obj.name;
            messenger('send', json_dump(outgoing));
            rep = messenger('recv');
            rep = json_load(rep);
        end

        function [] = run_code(obj, recipient_name, code)
            outgoing = {};
            outgoing.command = 'run_code';
            outgoing.name = obj;
            outgoing.args = {};
            outgoing.args.recipient_name = recipient_name;
            outgoing.args.code = code;
            messenger('send', json_dump(outgoing));
            messenger('recv'); % Receive an OK to set state back to "sender"
        end
    end
end
