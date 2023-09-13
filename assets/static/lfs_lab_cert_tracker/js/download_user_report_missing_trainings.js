$(document).ready(function() {

  $('#download-user-report-missing-trainings').on('click', function() {
    $(this).text('Downloading...');

    const self = this;
    $.ajax({
      method: 'GET',
      url: $(this).data('url'),
      data: $(this).data('next'),
      success: function(res) {
        $(self).text('Download All as CSV');

        if (res.status === 'success') {
          const filename = 'TRMS - Report - Missing Trainings ' + getToday() + '.csv';
          downloadCSV(res.data, filename);
        } else {
          const message = '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
                            'An error occurred while downloading all data' +
                            '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
                          '</div>';
          $('#download-csv-message').html(message);
        }
      },
      error: function(err) {
        $(self).text('Download All as CSV');

        const message = '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
                          'Error: ' + err.statusText + ' (' + err.status + '). ' + err.responseJSON.message +
                          '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
                        '</div>';
        $('#download-csv-message').html(message);
      }
    });
  });

});


/* Helper functions */

// Download data to a CSV file
function downloadCSV(data, filename) {
  let el = document.createElement('a');
  const blob = new Blob([data], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  el.href = url;
  el.setAttribute('download', filename);
  el.click();
}

// Get today's date format
function getToday() {
  var d = new Date(),
      month = '' + (d.getMonth() + 1),
      day = '' + d.getDate(),
      year = d.getFullYear();

  if (month.length < 2) month = '0' + month;
  if (day.length < 2) day = '0' + day;

  return [year, month, day].join('-');
}
