$(document).ready(function() {

  // Ininitally hide empty values in the form
  let after_hours_access_parent = $('#id_after_hours_access_0').parent();
  after_hours_access_parent.css('display', 'none');

  let building_name_parent = $('#id_building_name_0').parent();
  building_name_parent.css('display', 'none');

  // Affliation choices

  let aff_0 = $('#id_affliation_0');
  let aff_1 = $('#id_affliation_1');
  let aff_2 = $('#id_affliation_2');
  let aff_3 = $('#id_affliation_3');

  let employee_number_grand_parent = $('#id_employee_number').parent().parent();
  let student_number_grand_parent = $('#id_student_number').parent().parent();

  $('#id_affliation input').on('change', function() {
    remove_all_checked_attr(4, aff_0, aff_1, aff_2, aff_3, null);

    let curr = $(this).val();
    if (curr === '0') {
      aff_0.attr('checked', true);
      employee_number_grand_parent.css('display', 'table-row');
      student_number_grand_parent.css('display', 'none');

    } else if (curr === '1') {
      aff_1.attr('checked', true);
      student_number_grand_parent.css('display', 'table-row');
      employee_number_grand_parent.css('display', 'none');

    } else if (curr === '2') {
      aff_2.attr('checked', true);
      student_number_grand_parent.css('display', 'table-row');
      employee_number_grand_parent.css('display', 'none');

    } else if (curr === '3') {
      aff_3.attr('checked', true);
      employee_number_grand_parent.css('display', 'none');
      student_number_grand_parent.css('display', 'none');
    }
  });


  // After hours access choices

  let ahc_0 = $('#id_after_hours_access_0');
  let ahc_1 = $('#id_after_hours_access_1');
  let ahc_2 = $('#id_after_hours_access_2');
  remove_all_checked_attr(3, ahc_0, ahc_1, ahc_2, null);

  let working_alone_grand_parent = $('#id_working_alone').parent().parent();
  $('#id_after_hours_access input').on('change', function() {
    remove_all_checked_attr(3, ahc_0, ahc_1, ahc_2, null);

    let curr = $(this).val();
    if (curr === '0') {
      ahc_1.attr('checked', true);
      working_alone_grand_parent.css('display', 'table-row');
    } else if (curr === '1') {
      ahc_2.attr('checked', true);
      working_alone_grand_parent.css('display', 'none');
    }
  });


  // Building Name

  let bn_0 = $('#id_building_name_0');
  let bn_1 = $('#id_building_name_1');
  let bn_2 = $('#id_building_name_2');
  let bn_3 = $('#id_building_name_3');
  let bn_4 = $('#id_building_name_4');
  remove_all_checked_attr(5, bn_0, bn_1, bn_2, bn_3, bn_4);

  $('#id_building_name input').on('change', function() {
    remove_all_checked_attr(5, bn_0, bn_1, bn_2, bn_3, bn_4);

    let curr = $(this).val();
    if (curr === '0') {
      bn_1.attr('checked', true);
    } else if (curr === '1') {
      bn_2.attr('checked', true);
    } else if (curr === '2') {
      bn_3.attr('checked', true);
    } else if (curr === '3') {
      bn_4.attr('checked', true);
    }

  });

});

function remove_all_checked_attr(total, op_0, op_1, op_2, op_3, op_4) {
  op_0.removeAttr('checked');
  op_1.removeAttr('checked');
  op_2.removeAttr('checked');
  if (total >= 4) {
    op_3.removeAttr('checked');
  }
  if (total == 5) {
    op_4.removeAttr('checked');
  }
}
