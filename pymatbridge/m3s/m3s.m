classdef m3s
    methods(Static)
        function [] = start(name)
            json_startup;
            messenger('init', 'ipc:///tmp/m3c');
            messenger('send', name);
            response = messenger('recv')
        end

        function [] = exit()
            messenger('exit')
        end

        function [] = sync(var_name, broadcast)
            outgoing = {};
            if strcmp(var_name, '') == 1
                % Ask Python if it has anything to send
                outgoing.command = 'sync';
                outgoing.args = '';
                messenger('send', json_dump(outgoing));
                msg = messenger('recv')

                % Send the response back as a response command
                rep = pymat_eval(json_load(msg))
                outgoing.command = 'response';
                outgoing.args = rep;
                messenger('send', json_dump(outgoing));
                messenger('recv') % Receive an OK to set state back to "sender"
            else
                % Tell Python to pick a variable
                outgoing = {};
                if (broadcast == true)
                    outgoing.command = 'broadcast';
                else
                    outgoing.command = 'sync';
                end
                outgoing.args = var_name;
                messenger('send', json_dump(outgoing));
                msg = messenger('recv')

                % eval the code and send the response back
                rep = pymat_eval(json_load(msg))
                outgoing.command = 'response';
                outgoing.args = rep
                outgoing.meta = struct('var_name', var_name)
                messenger('send', json_dump(outgoing));
                messenger('recv') % Receive an OK to set state back to "sender"
            end
        end

        function [] = send_var(recipient_name, var_name)
            % Tell Python to pick a variable
            outgoing = {};
            outgoing.command = 'send';
            outgoing.args = var_name;
            messenger('send', json_dump(outgoing));
            msg = messenger('recv')

            % eval the code and send the response back
            rep = pymat_eval(json_load(msg))
            outgoing.command = 'response';
            outgoing.args = rep
            outgoing.meta = struct('var_name', var_name)
            outgoing.meta.recipient_name = recipient_name
            messenger('send', json_dump(outgoing));
            messenger('recv') % Receive an OK to set state back to "sender"
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
