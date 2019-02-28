% import common as k
<!DOCTYPE html>
<html lang="en" style="">
<head>
  <meta content="text/html; charset=utf-8" http-equiv="content-type">
  <meta charset="utf-8">
  <title>Supervisor Web Control</title>
  <meta content="width=device-width, initial-scale=1" name="viewport">
  <meta content="IE=edge" http-equiv="X-UA-Compatible">
  <link href="/static/css/sandstone.css" media="screen" rel="stylesheet">
  <link href="/static/css/font-awesome.min.css" rel="stylesheet">
  <link href="/static/css/supermon.css" rel="stylesheet">
</head>
<body>
  <div class="navbar navbar-expand-lg fixed-top navbar-dark bg-primary">
    <div class="container">
      <span class="navbar-brand" id="clear-template-cache">Supervisor Web Control</span>
        <div class="collapse navbar-collapse" id="navbarResponsive">
          <ul class="nav navbar-nav ml-auto">
            <li class="nav-item">
              <span id="sse-indicator" class="text-warning">
                <i class="fa fa-bolt fa-2x"></i>
              </span>
            </li>
            <li class="nav-separator">&nbsp;</li>
            <li class="nav-item">
              <span id="connection-indicator" class="bink-indicator text-danger">
                <i class="fa fa-server fa-2x"></i>
              </span>
            </li>
          </ul>
        </div>
    </div>
  </div>
  <div class="container">
    <div class="row">
      <div class="col-lg-12">
        <div>
          <form>
            <fieldset>
              <button data-command="{{! k.CMD_STOP_GLOB }}" class="btn btn-global btn-dark" id="btn-stop-all" type="button">
                <i class="fa fa-stop"></i>&nbsp;Stop all processes
              </button>
              <span>&nbsp;</span>
              <button data-command="{{! k.CMD_START_GLOB }}" class="btn btn-global btn-success" id="btn-start-all" type="button">
                <i class="fa fa-play"></i>&nbsp;Start all processes
              </button>
              <span>&nbsp;</span>
              <button data-command="{{! k.CMD_RESTART_GLOB }}" class="btn btn-global btn-primary" id="btn-restart-all" type="button">
                <i class="fa fa-refresh"></i>&nbsp;Restart all processes
              </button>
            </fieldset>
          </form>
        </div>
      </div>
    </div>
    <!-- Banner end -->

    <div class="bs-doc-section" style="margin-top:4em !important">
      % for ix, server in enumerate(data.get('servers')):
      % if ix % 2 == 0:
      <div class="row">
      % end
      % disable_btns = 'disabled' if server['failed'] else ''

        <div class="col-sm-6">
          <div class="card mb-3">
            <h3 class="card-header" id="server_name_{{! '{:02d}'.format(ix) }}">{{! server['server_name'] }}</h3>
            <div class="card-body">
              <h5 class="card-title">
                <button data-serv="{{! server['server_id'] }}" data-command="{{! k.CMD_STOP_ALL_PROC }}" class="btn btn-sm btn-dark btn-srv" type="button" {{! disable_btns }}>
                  <i class="fa fa-stop"></i>&nbsp;Stop all
                </button>
                <span>&nbsp;</span>
                <button data-serv="{{! server['server_id'] }}" data-command="{{! k.CMD_START_ALL_PROC }}" class="btn btn-sm btn-success btn-srv" type="button" {{! disable_btns }}>
                  <i class="fa fa-play"></i>&nbsp;Start all
                </button>
                <span>&nbsp;</span>
                <button data-serv="{{! server['server_id'] }}" data-command="{{! k.CMD_RESTART_ALL_PROC }}" class="btn btn-sm btn-primary btn-srv" type="button" {{! disable_btns }}>
                  <i class="fa fa-refresh"></i>&nbsp;Restart all
                </button>
              </h5>
              % if server['failed']:
              <div class="alert alert-dismissible alert-danger">
                <p></p>
                <h6>
                <div class="text-center">
                  <i class="fa fa-exclamation-triangle"></i><span>&nbsp;{{! server['error_message'] }}</span>
                </div>
                </h6>
                <p></p>
              </div>
              % end
              <!--
            </div>
            <div class="card-body">
            -->
              % # any processes to display?
              % if server['processes']:
              <table class="table table-hover table-sm">
                <thead>
                  <tr>
                    <th scope="col">Process</th>
                    <th class="status-col" scope="col">State</th>
                    <th class="runtime-col" scope="col">Runtime</th>
                    <th class="action-col" scope="col">&nbsp;</th>
                  </tr>
                </thead>
                <tbody>
                  % processes = [server['processes'][process_name] for process_name in sorted(server['processes'].keys())]
                  % for process in processes:
                  <tr>
                    <%
                    serv_proc = 'data-serv="{}" data-proc="{}"'.format(server['server_id'], process['process_id'])
                    id_serv_proc = '-{}-{}'.format(server['server_id'], process['process_id'])
                    statename = process.get('statename', '')

                    state_info = {
                      'RUNNING': {'alert': 'success', 'btn': 'dark', 'glyph': 'stop'},
                      'STOPPED': {'alert': 'dark', 'btn': 'success', 'glyph': 'play'},
                      'FATAL': {'alert': 'danger', 'btn': 'success', 'glyph': 'play'},
                      'STARTING': {'alert': 'primary', 'btn': 'light', 'glyph': 'ban'},
                    }
                    alert = 'success' if statename not in state_info else state_info[statename]['alert']
                    btn = 'light'  if statename not in state_info else state_info[statename]['btn']
                    glyph = 'ban' if statename not in state_info else state_info[statename]['glyph']

                    %>
                    <th role="row">{{! process['name'] }}</th>
                    <td><div  id="statename{{! id_serv_proc }}" class="statename-alert alert alert-{{! alert }}" role="alert" {{! serv_proc }} data-state="{{! statename }}" >
                      {{! statename }}</div>
                    </td>
                    <td><span id="runtime{{! id_serv_proc }}">{{! process.get('runtime', '') }}</span></td>
                    <td>
                      <button id="btn-proc{{! id_serv_proc }}" class="btn-process btn btn-sm btn-{{! btn }}" type="button" {{! serv_proc }} data-command="{{! k.CMD_TOGGLE_PROC }}" {{! disable_btns }}>
                        <i id="btn-glyph{{! id_serv_proc }}" class="fa fa-{{! glyph }}"></i>
                      </button>
                    </td>
                  </tr>
                  % end     # one process
                </tbody>
              </table>
              % end         # any processes
            </div>
          </div>
        </div>

      % if ix % 2 == 1:
      </div> <!-- row end -->
      % end
      % end     # for

      % # after last server... check if we need to close the row
      % if ix % 2 == 0:
      </div>
      % end

    </div>
    <!--  data end -->

    <footer id="footer">
      <div class="row">
        <div class="col-lg-12">
          <ul class="list-unstyled">
            <li class="float-lg-right">
              <a href="#top"><i class="fa fa-angle-double-up"></i>Back to top</a>
            </li>
            <li>
              Supervisor Monitor
            </li>
          </ul>
        </div>
      </div>
    </footer>

  </div>
  <script src="/static/js/jquery.js"></script>
  <script src="/static/js/popper.js"></script>
  <script src="/static/js/bootstrap.js"></script>
  <script src="/static/js/bootbox.min.js"></script>
  <script src="/static/js/hullabaloo.min.js"></script>
  <script src="/static/js/json2.js"></script>
  <script src="/static/js/uuid.js"></script>
  <script src="/static/js/supermon.js"></script>
</body>
</html>
