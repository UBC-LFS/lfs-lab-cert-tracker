$(document).ready(function() {
  $('.js-loading-submit').on('submit', function() {
    const submitInput = $(this).find('input[type=submit]');
    const loadingText = $(this).data('loading-text') || 'Updating...';
    submitInput.prop('disabled', true).val(loadingText);
  });
});