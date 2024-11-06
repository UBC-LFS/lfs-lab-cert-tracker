$(document).ready(function() {
  const paths = window.location.pathname.split('/');
  const len = paths.length;
  const currPageName = paths[len - 2];

  const uls = $('#left-side-menu').find('ul');
  for (const ul of uls) {
    const hyperlinks = $(ul).find('a');
    for (const hyperlink of hyperlinks) {
      $(hyperlink).parent().removeClass('active');

      const slug = slugify($(hyperlink).text());
      if (currPageName === slug) {
        $(hyperlink).parent().addClass('active');
      }
    }
  }
});

function slugify(str) {
  str = str.replace(/^\s+|\s+$/g, ''); // trim leading/trailing white space
  str = str.toLowerCase(); // convert string to lowercase
  str = str.replace(/[^a-z0-9 -]/g, '') // remove any non-alphanumeric characters
           .replace(/\s+/g, '-') // replace spaces with hyphens
           .replace(/-+/g, '-'); // remove consecutive hyphens
  return str;
}
