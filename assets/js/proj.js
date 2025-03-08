window.$doc = $(document)
window._status = {autoSaveOpt: false, editMode: false, selId: 1}

const ellipsisText = (s, n=10) => {
  if (s && s.length > n) {
    const n2 = parseInt(n / 2 + ''), s2 = s.replace(/\n/g, ' ')
    s = s.length > 12 && n > 8 ? s2.substring(0, n - n2 - 2).trim() + '……' + s2.substr(-n2).trim()
      : s2.substring(0, n - 1).trim() + '…'
  }
  return s
}

// 记录鼠标左键的按下状态
$doc.on('mousedown touchstart', '.columns-p', e => {
  _status.down = e.buttons === undefined || e.buttons === 1
  _status.clicked = false
  _status.x = e.pageX || 0
  _status.y = e.pageY || 0
})
$doc.on('mouseup touchend', '.columns-p', e => {
  _status.down = false
  _status.clicked = (Math.abs((e.pageX || 0) - _status.x) < 5
    && Math.abs((e.pageY || 0) - _status.y) < 5)
})

// 在行首标记点击等效于在段落上点鼠标右键显示上下文菜单
$doc.on('click', '.p-head', e => {
  $(e.target).next('p.text').trigger('contextmenu')
})

$doc.on('click', '.toggle-col', e => {
  const $li = $(e.target).closest('.toggle-col'), i = $li.data('i')
  $('.columns-p').toggleClass(`hide-col-${i}`)
  $(`.toggle-col[data-i="${i}"]`).toggleClass('active')
  if (_status.autoSaveOpt && window.options) {
    if (!$li.hasClass('active')) {
      options[`hide-col-${i}`] = !$li.hasClass('active')
    }
    saveOptions()
  }
})

function getProjId() {
  return $('[data-proj-id]').data('proj-id')
}

// 得到段落的行号、片段id、经典id、项目id
function getParaInfo($p, defVal=null) {
  const $c = $p.closest('.cell')
  return Object.assign({
    line: $p.data('line'), s_id: $p.data('s-id'),
    a_i: $c.data('i'), a_id: $c.data('id'),
    row_i: $c.closest('tr').data('row-i'),
    toc_i: $p.data('toc-i'), toc_id: $p.data('toc-id'),
    proj_id: window.getProjId && getProjId()
  }, $p.hasClass('toc_row') ? {} : {s_i: $p.data('s-i')}, defVal || {})
}

function _getTocRowByTreeNode($r) {
  const $tree = $r.closest('.toc-tree')
  if ($tree[0])
    return getTocRowByTreeNode($r, $tree.closest('[data-ext]').data('ext'))
}

window.activatePara = function($p, selectTocNode=false) {
  if (!$p.hasClass('active')) {
    $('p.active').removeClass('active')
    $p.addClass('active')
  }
  $('.cell.has-active').removeClass('has-active')
  $p.closest('.cell').addClass('has-active')

  if (selectTocNode && window.tocEnsureVisible) {
    tocEnsureVisible(getParaInfo($p, {element: $p[0]}))
  }
}

// 在单元格内点击段落
$doc.on('click', '.cell p.text', e => {
  const $t = $(e.target), $p = $t.closest('p');

  if (!_status.clicked) {
    return
  }
  $('.active-note').removeClass('active-note')
  $('p.has-active-note').removeClass('has-active-note')
  if ($t.hasClass('note-tag')) {
    const pn = $t.attr('data-pn'), nid = $t.attr('data-nid'),
      $np = $(`.note-p:has([data-pn="${pn}"])`);

    $t.toggleClass('expanded', _status.curNoteId !== nid || !$t.hasClass('expanded'))
    $np.toggleClass('expanded', $t.hasClass('expanded'))
    if (e.which === 1) {
      $np.find('.note-row').addClass('ellipsis-n')
      $np.find(`[data-nid="${nid}"] .note-row`).toggleClass('ellipsis-n')
    }
    _status.curNoteId = nid
    $(`[data-nid="${nid}"],.note-p [data-pn="${pn}"]`).addClass('active-note')
    $p.addClass('has-active-note')
    if (window.highLightNote) {
      highLightNote($t.hasClass('expanded') ? nid : '')
      const $hi = $('.cell-r .hi')
      scrollToVisible(document.querySelector('.cell-r'), $hi.first(), $hi.last())
    }
    return window.clearTimeout(_status.tmSel)
  }
  (window.clickCellP || $.noop)($p, e)
  activatePara($p, e.which === 1)
  if (e.which === 1 && $p.height() > 50) {
    if (_status.lastClick === $p[0]) {
      if (!$p.closest('.no-ellipsis')) {
        $p.toggleClass('ellipsis-n')
      }
    } else {
      if (!$(_status.lastClick || '-').closest('.no-ellipsis')) {
        $(_status.lastClick || '-').addClass('ellipsis-n')
      }
    }
    _status.lastClick = $p[0]
  }
  window.clearTimeout(_status.tmSel)
})

// 在单元格内点击科判条目
$doc.on('click', '.cell .toc_row', e => {
  const $p = $(e.target)
  activatePara($p, e.which === 1)
  if (e.which === 1 && ($p.height() > 40 || $p.hasClass('ellipsis'))) {
    if (_status.lastClick === $p[0]) {
      $p.toggleClass('ellipsis-n')
      $p.toggleClass('ellipsis', !$p.hasClass('ellipsis-n'))
    } else {
      if (!$(_status.lastClick || '-').closest('.no-ellipsis')) {
        $(_status.lastClick || '-').addClass('ellipsis-n')
      }
    }
    _status.lastClick = $p[0]
  }
})

// 点击注解元素
$doc.on('click', '.note-row', e => {
  const $t = $(e.target), $nid = $t.closest('[data-nid]'), nid = $nid.attr('data-nid')
  const toHide = $t.hasClass('note-row-end')
  if (!toHide && _status.curNoteId === nid) {
    $nid.find('.note-row').toggleClass('ellipsis-n')
  }
  _status.curNoteId = toHide ? nid : ''
  $(`.note-tag[data-nid="${nid}"]`).click()
})
$doc.on('click', '.note-p .close', e => {
  const $p = $(e.target).closest('.note-p'),
    nid = $p.find('.active-note[data-nid]').attr('data-nid') ||
      $p.find('[data-nid]').attr('data-nid')
  _status.curNoteId = nid
  $(`.note-tag[data-nid="${nid}"]`).click()
})

// 得到当前单元格选择的多个段落，跨列选择无效
function getSelectedTexts(shiftNode, allowSame=false) {
  const sel = document.getSelection(), texts = []
  const $end = $(shiftNode || sel.focusNode).closest('p.text')
  const col = $end.closest('.cell')[0]
  let $first = shiftNode ? $(col).find('.selected') : $(sel.anchorNode).closest('p.text')
  const up = $first[0] && $first.offset().top > ($end.offset() || {}).top

  if (up && shiftNode) {
    $first = $(col).find('.selected').last()
  }
  if ($first[0] && $end[0] && (allowSame || $first[0] !== $end[0]) && col) {
    for (let p = up ? $end : $first; p[0]; p = p.next()) {
      if (p.hasClass('text')) {
        if (col !== p.closest('.cell')[0]) {
          return [null, col, 'cross']
        }
        texts.push(p[0])
      }
      if (p[0] === (up ? $first : $end)[0]) {
        return [texts, col]
      }
    }
  }
  return [null, col]
}
