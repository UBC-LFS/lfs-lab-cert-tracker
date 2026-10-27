$(document).ready(function() {
  $('.js-loading-navigation').on('click', function() {
    const link = $(this);
    link.text(link.data('loading-text') || 'Loading...');
    link.addClass('disabled').attr('aria-disabled', 'true');
  });

  $('.js-loading-submit').on('submit', function(event) {
    // Use the button that started this submission; fall back for scripted submits.
    const clickedSubmit = event.originalEvent && event.originalEvent.submitter;
    const submitControl = clickedSubmit ? $(clickedSubmit) : $(this).find(':submit');

    // A button-level label overrides the form default (then the global fallback).
    const loadingText = submitControl.data('loading-text') || $(this).data('loading-text') || 'Updating...';

    // Disabled submit buttons are omitted from POST data. Preserve the clicked
    // button's name/value (for example, `method=Create Room`) before disabling it.
    if (clickedSubmit && clickedSubmit.name) {
      $('<input>', {
        type: 'hidden',
        name: clickedSubmit.name,
        value: clickedSubmit.value
      }).appendTo(this);
    }

    submitControl.prop('disabled', true);
    // Input submit controls display their label in `value`; buttons display text.
    if (submitControl.is('input')) {
      submitControl.val(loadingText);
    } else {
      submitControl.text(loadingText);
    }
  });
});
