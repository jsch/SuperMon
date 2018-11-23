application = function() {

    var connected = false;
    var session_id = null;
    var es = null;
    var ticks = 10 * 4;
    var serverSentEventsSupport = false;
    var disconnectNotified = false;
    var hulla = null;

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

        hulla = new hullabaloo();

        $('#clear-template-cache').on('click', function(e) {
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
        $('.btn-global').on('click', function(e){
            var command = $(this).data('command');
            console.log('Button global, action: ' + command);
            var request = {'command' : command};
            requestApiService(request);
            e.preventDefault();
        });

        // Server action buttons
        $('.btn-srv').on('click', function(e){
            var serv = $(this).data('serv');
            var command = $(this).data('command');
            console.log('Button server: ' + serv + ', action: ' + command);
            var request = {'command': command, 'server_id': serv};
            requestApiService(request);
            e.preventDefault();
        });

        // Process action buttons
        $('.btn-process').on('click', function(e){
            var serv = $(this).data('serv');
            var proc = $(this).data('proc');
            var command = $(this).data('command');
            var state_el = '#statename-' + serv + '-' + proc;
            var state = $(state_el).data('state');
            console.log('Button process: ' + serv + ', proc: ' + proc + ', command: ' + command, ', state: ' + state);
            var request = {'command': command, 'server_id': serv, 'process_id': proc, 'state': state};
            requestApiService(request);
            e.preventDefault();
        });

        /**
         * Request an API service
         */
        var requestApiService = function(request) {
            console.log('API:command:' + request.command);
            console.log('API:server_id:' + request.server_id);
            console.log('API:process_id:' + request.process_id);
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
            .always(function() {});
        };

        // **********************************************************
        // Server sent events
        //session_id = Math.uuid(15);
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
     * Connect to the server sent events
     */
    var doConnectSSE = function() {
        if (serverSentEventsSupport) {
            // Yes! Server-sent events support!
            session_id = Math.uuid(16);
            es = new EventSource('/stream/' + session_id);
            es.onmessage = function(e) {
                flashGlyph('#sse-indicator');
                console.log('SSE: ' + e.data);
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
            };
            es.onopen = function(e) {
                connected = true;
                disconnectNotified = false;
                console.log('SSE opened');
                hulla.send('Connected to server', 'success');
            };
            es.onerror = function(e) {
                connected = false;
                console.log('Error processing SSE stream');
                if (! disconnectNotified) {
                    hulla.send('Disconnected from server', 'danger');
                    disconnectNotified = true;
                }
            };
        } else {
            // Sorry! No server-sent events support..
        }
    };
    /**
     * Flash a glyph for 250 msec
     * @param {string} target elemento a flash
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
        // Check if it is time to send a keep-alive
        ticks --;
        if (ticks > 0) {
            return;
        }
        // Every 10 seconds send a keep-alive message to the server
        ticks = 10 * 4;
        request = {
            'command': 'keep-alive',
            'session_id': session_id
        };
        $.post('/api', request)
            .done(function(data, status, xhr) {
                try {
                    message = data.status;
                } catch (err) {
                    message = err;
                }
                console.log('KEEP: ' + message);
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
