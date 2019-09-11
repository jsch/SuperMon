/**
    search for:
        (slash)(slash)***
**/
var application = function() {
    'use strict';

    var connected = false;
    var session_id = null;
    // var es = null;
    var ticks = 10 * 4;
    var serverSentEventsSupport = false;
    var disconnectNotified = false;
    var hulla = null;
    var lightsOn = false;

    /**
     * Initiliaze the application
     */
    var doInit = function() {
        $(window).scroll(function() {
            /* */
            var top = $(document).scrollTop();
            if(top > 50)
              $('#home > .navbar').removeClass('navbar-transparent');
            else
              $('#home > .navbar').addClass('navbar-transparent');
            /* */
        });

        bootbox.setLocale('en');
        hulla = new hullabaloo();

        $('.btn-logout').on('click', function(e) {
            console.log('Logging out');
            var data = {
                'command': 'logout',
                'sessionid': session_id
            };
            $.post('/api', data)
                .done(function(data, status, xhr) {})
                .fail(function(data, status, xhr) {})
                .always(function(data, status, xhr) {
                    session_id = '';
                    location.reload(true);
                });
            e.preventDefault();
        });

        $('.clear-template-cache').on('click', function(e) {
            $.get('/clrtemplatecache')
                .done(function(data, status, xhr) {
                    bootbox.alert('Template cache cleared');
                })
                .fail(function(data, status, xhr) {
                    bootbox.alert('Error clearing template cache');
                })
                .always(function(data, status, xhr) {});
            e.preventDefault();
        });

        // Global action buttons
        $('.btn-global').on('click', function(e) {
            var command = $(this).data('command');
            console.log('Button global, action: ' + command);
            var request = {'command' : command};
            //  requestApiService(request);
            bootbox.confirm({
                size: "small",
                message: '<div class="text-center"><h5><i class="text-danger fa fa-exclamation-triangle"></i> Are you sure?</h5></div>',
                callback: function(result) {
                    if (result) {
                        requestApiService(request);
                    }
                }
            });
            e.preventDefault();
        });

        // Server action buttons
        $('.btn-srv').on('click', function(e) {
            var serv = $(this).data('serv');
            var command = $(this).data('command');
            console.log('Button server: ' + serv + ', action: ' + command);
            var request = {'command': command, 'server_id': serv};
            //  requestApiService(request);
            bootbox.confirm({
                size: "small",
                message: '<div class="text-center"><h5><i class="text-danger fa fa-exclamation-triangle"></i> Are you sure?</h5></div>',
                callback: function(result) {
                    if (result) {
                        requestApiService(request);
                    }
                }
            });
            e.preventDefault();
        });

        // Process action buttons
        $('.btn-process').on('click', function(e) {
            var serv = $(this).data('serv');
            var proc = $(this).data('proc');
            var command = $(this).data('command');
            var state_el = '#statename-' + serv + '-' + proc;
            var state = $(state_el).data('state');
            console.log('Button process: ' + serv + ', proc: ' + proc + ', command: ' + command, ', state: ' + state);
            var request = {'command': command, 'server_id': serv, 'process_id': proc, 'state': state};
            requestApiService(request);
        });

        /**
         * Request an API service
         */
        var requestApiService = function(request) {
            console.log('API:command:' + request.command);
            console.log('API:server_id:' + request.server_id);
            console.log('API:process_id:' + request.process_id);
            $('body').addClass('wait');
            $.post('/api', request)
            .done(function(data, status, xhr) {
                if (data) {
                    if (data.status === 'error') {
                        hulla.send(data.message, 'danger');
                    }
                }
            })
            .fail(function() {
                hulla.send('Error executing command', 'danger');
            })
            .always(function() {
                $('body').removeClass('wait');
            });
        };

        // **********************************************************
        // Server sent events
        // session_id = Math.uuid(16);
        serverSentEventsSupport = (typeof(EventSource) !== undefined);
        // **********************************************************
        // End of doInit()
        // **********************************************************
    };

    /**
     * Show an error message in a 'pop-up'
     */
    var showError = function(message) {
        if (message) {
            bootbox.alert({
                size: 'large',
                message: message
            });
        }
    };
    /**
     * Get the session_id
     * @return the current session_id or a new one is created.
     */
    var getSessionId = function() {
        if (! session_id) {
            session_id = Math.uuid(16);
        }
        return session_id;
    };
    /**
     * Connect to the server sent events
     */
    var doConnectSSE = function() {
        if (!serverSentEventsSupport) {
            // Sorry! No server-sent events support..
            return;
        }
        // Yes! Server-sent events support!
        var es = new EventSource('/stream/' + getSessionId())
            .onmessage(function(e) {
                if (! e) {
                    es.close();
                    console.log('SSE.onmessage no event');
                    return;
                }
                flashGlyph('#sse-indicator');
                //*** console.log('SSE: ' + e.data);
                try {
                    var data = JSON.parse(e.data);
                    if (data.type === 'event') {
                        var serv_proc = '-' + data.event.server_id + '-' + data.event.process_id;
                        var el = '#' + data.event.key + serv_proc;
                        $(el).text(data.event.to);
                        if (data.event.key === 'statename') {
                             // remove current classes and button glyph
                             $('#statename' + serv_proc).removeClass('alert-dark alert-success alert-emergency alert-primary');
                             $('#btn-proc' + serv_proc).removeClass('btn-dark btn-success btn-emergency btn-primary');
                             $('#btn-glyph' + serv_proc).removeClass('fa-start fa-stop');
                             var state_attr = {statename: 'light', btn: 'light', glyph: 'stop'};
                             // determine classes depending on current state
                             switch (data.event.to) {
                                case 'STOPPED':
                                    state_attr = {statename: 'dark', btn: 'success', glyph: 'play'};
                                    break;
                                case 'RUNNING':
                                    state_attr = {statename: 'success', btn: 'dark', glyph: 'stop'};
                                    break;
                                case 'FATAL':
                                    state_attr = {statename: 'danger', btn: 'success', glyph: 'play'};
                                    break;
                                case 'STARTING':
                                    state_attr = {statename: 'primary', btn: 'light', glyph: 'stop'};
                                    break;
                                default:
                                    break;
                             }
                             $('#statename' + serv_proc).addClass('alert-' + state_attr.statename);
                             $('#btn-proc' + serv_proc).addClass('btn-' + state_attr.btn);
                             $('#btn-glyph' + serv_proc).addClass('fa-' + state_attr.glyph);
                             $('#statename' + serv_proc).data('state', data.event.to);

                             hulla.send('Process ' + data.event.process_name + ' is ' + data.event.to, state_attr.statename);
                         }
                    }
                } catch(err) {
                    console.log('Exception: ' + err + ', data: ' + e.data);
                }
            })
            .onopen(function(e) {
                connected = true;
                disconnectNotified = false;
                console.log('SSE opened');
                hulla.send('Connected to server', 'success');
            })
            .onerror(function(e) {
                connected = false;
                console.log('Error processing SSE stream');
                if (! disconnectNotified) {
                    hulla.send('Disconnected from server', 'danger');
                    disconnectNotified = true;
                    session_id = null;
                }
            }
        );
    };
    /**
     * Flash a glyph for 250 msec
     * @param {string} target element to flash
     */
    var flashGlyph = function(target) {
        $(target).removeClass('invisible').addClass('visible');
        setTimeout(function() {
            $(target).addClass('invisible').removeClass('visible');
        }, 250);
    };
    /**
     * Blink status
     */
    var lightsOn = false;
    var doBlinkenLights = function() {
        if (! lightsOn) {
            $('.bink-indicator').hide();
        } else {
            if (! connected) {
                $('#connection-indicator').show();
            }
        }
        lightsOn = ! lightsOn;
    };
    /**
     * Timer update. It is called every 250 msec.
     * n.b. One second is every 4 ticks
     */
    var doUpdate = function() {
        // Update blinking indicators
        doBlinkenLights();

        // Try to reconnect every 5 seconds if server is down
        if (! connected && (ticks % (5 * 4) == 0)) {
            doConnectSSE();
        }
        // Check if it is time to send a keep_alive
        ticks --;
        if (ticks > 0) {
            return;
        }
        // Every 10 seconds send a keep_alive message to the server
        ticks = 10 * 4;
        var _session_id = getSessionId();
        var request = {
            'command': 'keep_alive',
            'session_id': _session_id
        };
        console.log('KEEP-ALIVE:SESSION:' + _session_id);
        $.post('/api', request)
            .done(function(data, status, xhr) {
                var message;
                try {
                    message = data.status;
                } catch (err) {
                    message = err;
                }
                console.log('KEEP-ALIVE:ACK:' + message);
            })
            .fail(function(data, status, xhr) {})
            .always(function(data, status, xhr) {});
    };
    /**
     * Available functions
     */
    return {
        init: function() {
            doInit();
        },
        update: function() {
            doUpdate();
        },
        connectSSE: function() {
            doConnectSSE();
        },
        getSessionId: function() {
            return session_id;
        }
    };
}();

function updater() {
    application.update();
    setTimeout(updater, 250);
}
application.init();
updater();

// EOF
