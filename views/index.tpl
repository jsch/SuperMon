<!DOCTYPE html>

<html>
<head>
    <meta content="text/html; charset=utf-8" http-equiv="content-type">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="utf-8">
    <title>Supervisor Web Control</title>
    <meta content="width=device-width, initial-scale=1" name="viewport">
    <meta content="IE=edge" http-equiv="X-UA-Compatible">
    <link href="/static/css/sandstone.css" media="screen" rel="stylesheet">
    <link href="/static/css/font-awesome.min.css" rel="stylesheet">
    <link href="/static/css/supermon.css" rel="stylesheet">
    <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!--[if lt IE 9]>
      <script src="/js/html5shiv.js"></script>
      <script src="/js/respond.min.js"></script>
    <![endif]-->
    <style>
        .wait, .wait * {cursor: wait !important;}
        .cursor-pointer {cursor: pointer !important;}
        % if data.get('background'):
        .w-backgound {background: url("/static/images/{{! data.get('background') }}")}
        % end
        /* */
  </style>
</head>

<body id="page-body" class="w-backgound">
    <div id="main">
    </div>
    <div id="div-modal-login" class="container bs-docs-container">
        <div class="modal fade" id="loginModal" tabindex="-1" role="dialog" aria-labelledby="loginModalLabel" aria-hidden="true"
             data-backdrop="static" data-keyboard="false">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <!--button type="button" class="close" data-dismiss="modal" aria-hidden="true">&#215;</button-->
                        <h4 class="modal-title" id="loginModalLabel">Supervisor Monitor</h4>
                    </div>

                    <div class="modal-body">
                        <div id="modal-body">

                            <form class="form-horizontal" role="form" id="frm-login">
                                <div class="form-group">
                                    <label for="txt-username" class="col-sm-3 control-label">Username</label>
                                    <div class="col-sm-12">
                                        <input type="text" class="form-control" id="txt-username" placeholder="Username" vlue="">
                                    </div>
                                </div>

                                <div class="form-group">
                                    <label for="txt-user-password" class="col-sm-3 control-label">Password</label>
                                    <div class="col-sm-12">
                                        <input type="password" class="form-control" id="txt-user-password" placeholder="Password" vlue="">
                                    </div>
                                </div>

                                <div id="alert-authenticating-user" class="alert alert-info hidden" role="alert" aria-hidden="true">
                                    <p>
                                      <img id="img-status-ejecucion-comando" src="/static/images/loading.gif">
                                      <span><strong>Authenticating user. Please wait.</strong></span>
                                    </p>
                                </div>

                                <div class="alert alert-danger login-error" id="alert-error-login" aria-hidden="true">
                                    <strong>Error:</strong> </br><span id="login-error-type">Invalid username or password.</span>
                                </div>
                            </form>
                        </div>
                    </div>

                    <div class="modal-footer">
                        <!--
                        <h6 class="float-left"><small>{{ data.get('git_tag', '--FIX GIT TAG--') }}</small></h6>
                        -->
                        <button type="submit" class="btn btn-primary" id="btn-login">
                            <span class="fa fa-sign-in" aria-hidden="true"></span>&nbsp;&nbsp;Login
                        </button>
                    </div>
                </div><!-- /.modal-content -->
            </div><!-- /.modal-dialog -->
        </div><!-- /.modal -->
    </div>


    <script type="text/javascript" src="/static/js/jquery.js"></script>
    <script type="text/javascript" src="/static/js/popper.js"></script>
    <script type="text/javascript" src="/static/js/bootstrap.js"></script>
    <script type="text/javascript" src="/static/js/bootbox.min.js"></script>
    <script type="text/javascript" src="/static/js/hullabaloo.min.js"></script>
    <script type="text/javascript" src="/static/js/json2.js"></script>
    <script type="text/javascript" src="/static/js/uuid.js"></script>
    <script type="text/javascript" src="/static/js/base64.js"></script>
    <script type="text/javascript" src="/static/js/appinit.js"></script>
</body>
</html>
