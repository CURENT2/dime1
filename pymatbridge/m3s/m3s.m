classdef m3s
    methods(Static)
        function [] = start()
            json_startup;
            messenger('init', 'ipc:///tmp/m3c');
            messenger('send', 'connect');
            messenger('recv')
        end

        function [] = sync(var_name)
            outgoing = {};
            if ~exist('var_name', 'var')
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
                messenger('recv') % Receive an OK to set the state back to "sender"
            else
                % Tell Python to pick a variable
                outgoing = {};
                outgoing.command = 'sync';
                outgoing.args = var_name;
                messenger('send', json_dump(outgoing));
                msg = messenger('recv')

                % eval the code and send the response back
                rep = pymat_eval(json_load(msg))
                outgoing.command = 'response';
                outgoing.args = rep;
                messenger('send', json_dump(outgoing));
                messenger('recv') % Receive an OK to set the state back to "sender";
            end
        end
    end
end
