function onPswChanged(el) {
  setTimeout(() => {
    const chk = [el.value.length > 5, /[A-Z]/.test(el.value), /[a-z]/.test(el.value),
      /[0-9]/.test(el.value), /[~!@#$%_;,.]/.test(el.value)]
    const inv = /[^A-Za-z0-9~!@#$%_;,.]/.test(el.value)
    const n = chk.reduce((a, c) => a + c, 0), ok = !inv && chk[0] && n > 2

    $('#p-len').text(`${el.value.length} 字符`).toggleClass('ok', chk[0])
    $('#p-upper').toggleClass('ok', chk[1])
    $('#p-lower').toggleClass('ok', chk[2])
    $('#p-digit').toggleClass('ok', chk[3])
    $('#p-sign').toggleClass('ok', chk[4])
    $(el).closest('.form-control').toggleClass('error', inv)
    $('#p-ok').text(inv ? '✘' : ok ? '✔' : '').toggleClass('ok', ok)
  }, 50)
}