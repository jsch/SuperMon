/**
 * Aplicacion del Front-End del ejercitador generico
 *
 */
const appInit = function() {
    'use strict';
    var numActiveRequests = 0;
    var doingLogin = false;

    var doAjaxBeforeSend = function() {
        numActiveRequests++;
        $('#loading-indicator').removeClass('hidden');
        $('#page-body').addClass('wait');
    };
    var doAjaxComplete = function() {
        if (numActiveRequests > 0) {
            numActiveRequests--;
        }
        if (numActiveRequests < 1) {
            $('#page-body').removeClass('wait');
            $('#loading-indicator').addClass('hidden');
        }
    };
    var loadDiv = function(b64, div) {
        var html = (b64 ? Base64.decode(b64) : '');
        $(div).html(html);
    };
    var doLogin = function(){
        if (doingLogin) {
            return;
        }
        // Hide errors
        $('#page-body').addClass('wait');
        $('.login-error').hide();
        doingLogin = true;
        $('#alert-authenticating-user').show();
        var data = {
            'command': 'authenticateuser',
            'username': $('#txt-username').val(),
            'password': $('#txt-user-password').val()
        };
        $.post('/api', data)
            .done(function(data, status, xhr) {
                if (data.result === 'ok') {
                    $('#loginModal').modal('hide');
                    loadDiv(data.html, '#main');
                } else if (data.result === 'error') {
                    shakeLogin();
                    $('#login-error-type').html(data.message);
                    $('#alert-error-login').show();
                } else { //if (data.result == 'ERROR-DESCONOCIDO')
                    $('#login-error-type').html('An unexpected error occurred.<br />Pleas contact the administrator.');
                    $('#alert-error-login').show();
                }
            })
            .fail(function(data, status, xhr) {
                $('#login-error-type').html('No communications with the server. Is it running?');
                $('#alert-error-login').show();
            })
            .always(function(data, status, xhr) {
                $('#alert-authenticating-user').hide();
                $('#page-body').removeClass('wait');
                doingLogin = false;
            })
        ;
    };
    var shakeLogin = function() {
        $('#loginModal').addClass('wiggle');
        setTimeout(function() {
            $('#loginModal').removeClass('wiggle');
            doLogin();
        }, 1000);
    };
    var doInit = function() {
        // Disable cache for Ajax
        $.ajaxSetup({
            cache: false,
            ajaxBeforeSend: doAjaxBeforeSend,
            ajaxComplete: doAjaxComplete,
            async: true
        });
        $('.login-error').hide();
        $('#alert-authenticating-user').hide();
        $('#loginModal').modal('show');
        setTimeout(function() {
            $('#txt-username').focus();
        }, 1000);
        $('#frm-login').on('submit', function(e){
            e.preventDefault();
            doLogin();
        });
        $('#btn-login').on('click', function(e){
            e.preventDefault();
            doLogin();
        });
        $('#frm-login').keypress(function (e){
            if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
                doLogin();
                return false;
            }
            return true;
        });
    };
    return {
        init: function() {
            doInit();
        }
    };
}();
$(document).ready(function() {
    $('[data-toggle="tooltip"]').tooltip();
    // Start thw application
    appInit.init();
});
