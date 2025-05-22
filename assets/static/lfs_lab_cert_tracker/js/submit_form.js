$(document).ready(function() {
  const empl = $('#id_employee_number');
  const stud = $('#id_student_number');
  const working_alone = $('#id_working_alone');

  const empl_parent = empl.parent().parent();
  const stud_parent = stud.parent().parent();
  const working_alone_parent = working_alone.parent().parent();

  // Affliation choices
  $('#id_affliation input').on('change', function() {
    const id = this.value;
    if (id === '0') {
      empl_parent.css('display', 'table-row');
      stud_parent.css('display', 'none');
      empl.attr('required', true);
      stud.removeAttr('required');
    } else if (id === '1' || id === '2') {
      stud_parent.css('display', 'table-row');
      empl_parent.css('display', 'none');
      stud.attr('required', true);
      empl.removeAttr('required');
    } else if (id === '3') {
      empl_parent.css('display', 'none');
      stud_parent.css('display', 'none');
      empl.removeAttr('required');
      stud.removeAttr('required');
    }
  });

  // After hours access choices
  $('#id_after_hours_access input').on('change', function() {
    const id = this.value;
    if (id === '0') {
      working_alone_parent.css('display', 'table-row');
      working_alone.attr('required', true);
    } else if (id === '1') {
      working_alone_parent.css('display', 'none');
      working_alone.removeAttr('required');
    }
  });
});
