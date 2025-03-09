try {
  window.options = JSON.parse(localStorage.getItem('cbsOptions'))
} catch (e) {}
if (!window.options || typeof window.options !== 'object') {
  window.options = {theme: 'warm'}
}
if (options.theme) {
  $('html').attr('data-theme', options.theme)
}

function updateThemeMenu() {
  $('[id^="theme-"]').each(function () {
    const theme = this.getAttribute('id').replace('theme-', '')
    $(this).closest('li').toggleClass('active', options.theme === theme)
  })
}

function saveOptions() {
  localStorage.setItem('cbsOptions', JSON.stringify(options))
}

$(function () {
  $('[id^="theme-"]').click(e => {
    const value = e.target.getAttribute('id').replace('theme-', '')
    const theme = options.theme === value ? 'default' : value
    options.theme = theme
    $('html').attr('data-theme', options.theme)
    saveOptions()
    updateThemeMenu()
  })
  updateThemeMenu()
})
