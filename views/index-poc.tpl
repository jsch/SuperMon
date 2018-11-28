<!DOCTYPE html>
<html lang="en" style="">
<head>
  <meta content="text/html; charset=utf-8" http-equiv="content-type">
  <meta charset="utf-8">
  <title>Supervisor Web Control</title>
  <meta content="width=device-width, initial-scale=1" name="viewport">
  <meta content="IE=edge" http-equiv="X-UA-Compatible">
  <link href="/static/css/bootstrap.css" media="screen" rel="stylesheet">
  <link href="/static/css/font-awesome.min.css" rel="stylesheet">
  <link href="/static/css/supermon.css" rel="stylesheet">
</head>
<body>
  <div class="navbar navbar-expand-lg fixed-top navbar-dark bg-primary">
    <div class="container">
      <span class="navbar-brand" id="clear-template-cache">Supervisor Web Control</span>
    </div>
  </div>
  <div class="container">
    <div class="row">
      <div class="col-lg-12">
        <div>
          <form>
            <fieldset>
              <div class="form-group">
                <!-- <label for="exampleTextarea">Comando</label> -->
                <!-- <textarea id="txt-sql" class="form-control" id="exampleTextarea" rows="3"></textarea> -->
              </div>
              <button class="btn btn-secondary" id="btn-stop-all" type="button"><i class="fa fa-stop"></i>&nbsp;Stop all processes</button>
              <span>&nbsp;</span>
              <button class="btn btn-success" id="btn-start-all" type="button"><i class="fa fa-play"></i>&nbsp;Start all processes</button>
              <span>&nbsp;</span>
              <button class="btn btn-primary" id="btn-restart-all" type="button"><i class="fa fa-refresh"></i>&nbsp;Restart all processes</button>
            </fieldset>
          </form>
        </div>
      </div>
    </div>
    <div class="hidden" id="please-wait-message">
      <div class="alert alert-dismissible alert-light">
        <button class="close" data-dismiss="alert" type="button">&times;</button>
        <p></p>
        <div class="text-center">
          <i class="fa fa-spin fa-spinner"></i> Executing, please wait...
        </div>
        <p></p>
      </div>
    </div>

    <div class="bs-docs-section">
      <div class="row">
        <div class="col-sm-6">
          <div class="card mb-3">
            <h3 class="card-header">Server-01</h3>
            <div class="card-body">
              <h5 class="card-title">
                <button class="btn btn-secondary btn-sm" type="button">Stop all</button>
                <button class="btn btn-success btn-sm" type="button">Start all</button>
                <button class="btn btn-primary btn-sm" type="button">Restart all</button>
              </h5>
              <h6 class="card-subtitle text-muted">Support card subtitle</h6>
            </div>
            <div class="card-body">
              <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
            </div>
            <ul class="list-group list-group-flush">
              <li class="list-group-item">Cras justo odio</li>
              <li class="list-group-item">Dapibus ac facilisis in</li>
              <li class="list-group-item">Vestibulum at eros</li>
            </ul>
            <div class="card-body">
              <a class="card-link" href="#">Card link</a> <a class="card-link" href="#">Another link</a>
            </div>
            <div class="card-footer text-muted">
              2 days ago
            </div>
          </div>
        </div>

        <div class="col-sm-6">
          <div class="card mb-3">
            <h3 class="card-header">Server-02</h3>
            <div class="card-body">
              <h5 class="card-title">
                <button class="btn btn-secondary btn-sm" type="button"><i class="fa fa-stop"></i>&nbsp;Stop all</button>&nbsp;
                <button class="btn btn-success btn-sm" type="button"><i class="fa fa-play"></i>&nbsp;Start all</button>&nbsp;
                <button class="btn btn-primary btn-sm" type="button"><i class="fa fa-refresh"></i>&nbsp;Restart all</button>
              </h5>
            </div>
            <div class="card-body">
              <table class="table table-hover table-sm">
                <thead>
                  <tr>
                    <th scope="col">Process</th>
                    <th class="status-col" scope="col">Status</th>
                    <th class="runtime-col" scope="col">Runtime</th>
                    <th class="action-col" scope="col">&nbsp;</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">Process 1</th>
                    <!-- <td><span class="badge badge-secondary">STOPPED</span></td> -->
                    <td><div class="alert alert-secondary" role="alert">STOPPED</div></td>
                    <td>&nbsp;</td>
                    <td><button class="btn btn-success btn-sm" type="button"><i class="fa fa-play"></i></button></td>
                  </tr>
                  <tr>
                    <th scope="row">Process 2</th>
                    <!-- <td><span class="badge badge-success">RUNNING</span></td> -->
                    <td><div class="alert alert-success" role="alert">RUNNING</div></td>
                    <td>999 days 00:00:00</td>
                    <td><button class="btn btn-secondary btn-sm" type="button"><i class="fa fa-stop"></i></button></td>
                  </tr>
                  <tr>
                    <th scope="row">Process 3</th>
                    <!-- <td><span class="badge badge-danger">FATAL</span></td> -->
                    <td><div class="alert alert-danger" role="alert">FATAL</div></td>
                    <td>&nbsp;</td>
                    <td><button class="btn btn-success btn-sm" type="button"><i class="fa fa-play"></i></button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>
    </div>


    <footer id="footer">
      <div class="row">
        <div class="col-lg-12">
          <ul class="list-unstyled">
            <li class="float-lg-right">
              <a href="#top"><i class="fa fa-angle-double-up"></i>Back to top</a>
            </li>
            <li>
              <a href="http://encontrack.com/">Encontrack</a>
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
</body>
</html>
