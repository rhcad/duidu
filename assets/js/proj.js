window.$doc = $(document)
window._status = {autoSaveOpt: false, editMode: false}

// 记录鼠标左键的按下状态
$doc.on('mousedown mouseup', '.columns-p', e => {
  _status.down = e.buttons === 1
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

function activatePara($p, selectTocNode=false) {
  if (!$p.hasClass('active')) {
    $('p.active').removeClass('active')
    $p.addClass('active')
  }
  $('.cell.has-active').removeClass('has-active')
  $p.closest('.cell').addClass('has-active')

  if (!$p.hasClass('text')) {
    $('p.selected', $p.closest('.cell')).removeClass('selected')
  }
  if (selectTocNode && window.tocEnsureVisible) {
    tocEnsureVisible(getParaInfo($p, {element: $p[0]}))
  }
  window.clearTimeout(_status.tm)
}

// 得到当前单元格选择的多个段落，跨列选择无效
function _getSelectedTexts(shiftNode) {
  const sel = document.getSelection(), texts = []
  const $end = $(shiftNode || sel.focusNode).closest('p.text')
  const col = $end.closest('.cell')[0]
  let $first = shiftNode ? $(col).find('.selected') : $(sel.anchorNode).closest('p.text')
  const up = $first[0] && $first.offset().top > ($end.offset() || {}).top

  if (up && shiftNode) {
    $first = $(col).find('.selected').last()
  }
  if ($first[0] && $end[0] && $first[0] !== $end[0] && col) {
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

function _getTocRowByTreeNode($r) {
  const $tree = $r.closest('.toc-tree')
  if ($tree[0])
    return getTocRowByTreeNode($r, $tree.closest('[data-ext]').data('ext'))
}

// 在单元格内点击段落
$doc.on('click', '.cell p.text', e => {
  const $p = $(e.target), $cell = $p.closest('.cell')

  if (_status.editMode) {
    const oldSel = $('.selected'), oldIsSel = $p.hasClass('selected')
    const sel_ = _getSelectedTexts(e.shiftKey && e.target)
    const sel = sel_[0] || [] // 当前单元格的选中段落

    document.getSelection().empty()
    _clearOtherRowsSelected($p)
    $cell.find('.selected').removeClass('selected') // 当前TR的其它列的选择不变

    if (e.shiftKey) {
      sel.forEach(p => $(p).addClass('selected'))
    } else if (!oldIsSel || oldSel.length !== 1 || (sel.length === 1 && sel[0] !== e.target)) {
      $p.addClass('selected')
    } // else: toggle selected
    _showSelectedTip($cell)
  }

  activatePara($p, e.which === 1)
  if (e.which === 1 && $p.height() > 50) {
    if (_status.lastClick === $p[0]) {
      $p.toggleClass('ellipsis-n')
    } else {
      $(_status.lastClick || '-').addClass('ellipsis-n')
    }
    _status.lastClick = $p[0]
  }
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
      $(_status.lastClick || '-').addClass('ellipsis-n')
    }
    _status.lastClick = $p[0]
  }
})
