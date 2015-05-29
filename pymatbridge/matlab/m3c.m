json_startup
messenger('init', 'ipc:///tmp/m3c')
messenger('listen')
messenger('respond', 'connected')
messenger('listen')
messenger('respond', pymat_eval(json_load(ans)))