function swalWillOpen(){
  const $w = $('.swal-autoscroll'), h = $w.height()
  $w.first().css('height', h + 'px')
}
function swalWillClose(){
  const $w = $('.swal-autoscroll'), h = $w.height()
  setTimeout(() => $w.css('height', ''), 200)
}

window.Swal = Swal.mixin({ willOpen: swalWillOpen, willClose: swalWillClose })
window.Swal0 = Swal.mixin({ showConfirmButton: false })
window.Swal1 = Swal0.mixin({ showCancelButton: true, cancelButtonText: '关闭' })
window.Swal2 = Swal.mixin({ confirmButtonText: '确定', showCancelButton: true, cancelButtonText: '取消' })

function showError(title, text, ended) {
  text = (text || '').replace(/^.*<body>(\d+: )?|<\/body>.*$/g, '')
  Swal0.fire({
    title: title, text: text, timer: 2000,
    icon: /失败|错误|error/.test(title) ? 'error' : 'warning',
  })
  if (ended) setTimeout(ended, 2000)
  return false
}
function showSuccess(title, text, ended) {
  Swal0.fire({title: title, text: text, icon: 'success', timer: 1000})
  if (ended) setTimeout(ended, 1000)
}
function ajaxError(title, op) {
  return xhr => showError(title, `[${xhr.status}] ${xhr.responseText}`, op);
}

function isSwalInputVisible() {
  return $('.swal2-textarea,.swal2-input,.swal2-select').is(':visible')
}
function ajaxApi(url, type, data, success_callback, error_callback) {
  data = data || {}
  if (typeof data.data === 'object') {
    data.data = JSON.stringify(data.data)
  }
  if (!error_callback && isSwalInputVisible()) {
    error_callback = obj => Swal.showValidationMessage(obj.message)
  }
  error_callback = error_callback || (obj => showError('操作失败', obj.message))
  success_callback = success_callback || console.log

  url = url.substr(0, 4) === '/api' ? url : '/api' + url;
  const $modal = $('.modal-open .modal-content,.swal2-popup,.wait').addClass('wait')
  const on_error = obj => console.log(obj) || error_callback(obj)
  const on_success = data => {
    $modal.removeClass('wait')
    if (data.status === 'failed') {
      on_error(data)
    } else {
      $.extend(data, data.data && typeof data.data === 'object' && !Array.isArray(data.data) ? data.data : {})
      success_callback(data)
    }
  }
  const params = {
    url: url,
    type: type,
    cache: false,
    crossDomain: true,
    xhrFields: {withCredentials: true},
    success: on_success,
    error: function (xhr) {
      const code = xhr.status || xhr.code || 500
      $modal.removeClass('wait')
      if (code >= 200 && code <= 299) {
        try {
          const data = JSON.parse(xhr.responseText)
          if (data && typeof data.status === 'string') {
            success_callback(data)
            return
          }
        } catch (e) {}
        success_callback({})
      } else {
        on_error({code: code, message: `网络访问失败 (${code})`})
      }
    }
  }

  const file = data.file, dataType = data.dataType
  delete data.file
  delete data.dataType
  if (file) {
    params['data'] = data
    params['processData'] = false
    params['contentType'] = false
  } else {
    params['data'] = $.param(data)
    params['dataType'] = dataType || 'json'
  }

  return $.ajax(params)
}

/**
 * 以GET方式调用后端接口
 * @param {string} url 以“/”开头的地址
 * @param {Function} [success] 成功回调函数，可选，参数为 data 对象或数组
 * @param {Function} [error] 失败回调函数，可选，参数为 msg、code
 */
function getApi(url, success, error) {
  return ajaxApi(url, 'GET', null, success, error)
}
function renderApi(success, url='') {
  return ajaxApi(url || location.pathname, 'GET', {dataType: 'html'}, success, reloadPage)
}

/**
 * 以POST方式调用后端接口
 * @param {string} url 以“/”开头的地址
 * @param {object} data 请求体JSON对象，可指定 file 表示传输文件
 * @param {Function} [success] 成功回调函数，可选，参数为 data 对象或数组
 * @param {Function} [error] 失败回调函数，可选，参数为 msg、code
 */
function postApi(url, data, success, error) {
  return ajaxApi(url, 'POST', data, success, error)
}

$.ajaxSetup({
  beforeSend: function (jqXHR, settings) {
    const type = settings.type
    if (type !== 'GET' && type !== 'HEAD' && type !== 'OPTIONS') {
      const xsrf = /(.+; *)?_xsrf *= *([^;" ]+)/.exec(document.cookie || '')
      if (xsrf) {
        jqXHR.setRequestHeader('X-Xsrftoken', xsrf[2])
      }
    }
  }
})

/**
 * 得到模态框的输入内容
 * @param $modal 模态框
 * @param fields 数据字段名数组，字段名可含下划线
 * @param [prefix] 输入框名称前缀
 * @returns {Object} fields 对应的数据对象
 */
function getModalData($modal, fields, prefix='') {
  const data = {}
  for (let i in fields) {
    const fd = fields[i], f = fd.replace('_', '-')
    const $f = $modal.find(`#modal-${f},[name="${f}"],[name="${prefix}-${f}"]`).first();

    console.assert($f[0], fd)
    if ($f.hasClass('modal-radio')) {
      const v = $f.find(':checked').val()
      if ($f.hasClass('bool')) {
        if (v) data[fd] = parseInt(v)
      } else {
        data[fd] = v
      }
    } else if ($f.is('select')) {
      data[fd] = $f.val()
    } else {
      data[fd] = ($f.val() || '').trim()
    }
    const no = ['', null, undefined].indexOf(data[fd]) >= 0
    if (no && ($f.hasClass('required') || $f[0].hasAttribute('required'))) {
      Swal0.fire({
        text: '请选择 ' + $f.closest('.row').find('.control-label').text().replace('*', ''),
        timer: 1000, customClass: 'w300'
      })
      return
    }
  }
  return data
}

function resetModalData($modal, fields, prefix='') {
  fields.forEach(field => {
    const f = field.replace('_', '-')
    const $field = $modal.find(`#modal-${f},[name="${f}"],[name="${prefix}-${f}"]`).first()
    $field.val('')
    $.map($field.find(':checked'), el => $(el).removeAttr('checked'))
    $.map($field.find(':selected'), el => $(el).removeAttr('selected'))
  })
}

function reloadPage() {
  window.location.reload()
}
