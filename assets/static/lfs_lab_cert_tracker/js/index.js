$(document).ready(function() {
  const path = window.location.href;

  const uls = $('#left-side-menu').find('ul');
  for (const ul of uls) {
    const hyperlinks = $(ul).find('a');
    for (const hyperlink of hyperlinks) {
      const href = hyperlink.href
      if (compareWithoutQueryParams(href, path)) {
        $(hyperlink).parent().addClass('active');
      } else {
        $(hyperlink).parent().removeClass('active');
      }

    }
  }
});

// Basic normalization -> should cover most cases
function compareWithoutQueryParams(href1, href2) {
  href1 = href1.split("?")[0];
  href2 = href2.split("?")[0];
  return href1 === href2;
}

// function slugify(str) {
//   str = str.replace(/^\s+|\s+$/g, ''); // trim leading/trailing white space
//   str = str.toLowerCase(); // convert string to lowercase
//   str = str.replace(/[^a-z0-9 -]/g, '') // remove any non-alphanumeric characters
//            .replace(/\s+/g, '-') // replace spaces with hyphens
//            .replace(/-+/g, '-'); // remove consecutive hyphens
//   return str;
// }
