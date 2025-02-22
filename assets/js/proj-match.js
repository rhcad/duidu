const $doc = $(document)
const _status = {}

// 记录鼠标左键的按下状态
$doc.on('mousedown mouseup', '.columns-p', e => {
  _status.down = e.buttons === 1
})

// 在行首标记点击等效于在段落上点鼠标右键显示上下文菜单
$doc.on('click', '.p-head', e => {
  $(e.target).next('p.text').trigger('contextmenu')
})
$doc.on('click', '.toggle-col', e => {
  const $li = $(e.target).closest('.toggle-col'), i = $li.data('i')
  $('.columns-p').toggleClass(`hide-col-${i}`)
  $li.toggleClass('active')
  if (!$li.hasClass('active')) {
    options[`hide-col-${i}`] = !$li.hasClass('active')
  }
  saveOptions()
})

// 清除其他TR的段落选择
function _clearOtherRowsSelected($p) {
  const ri = $p.closest('.columns').data('row-i')
  $(`.columns:not([data-row-i="${ri}"]) .selected`).removeClass('selected')
}

// 在单元格内点击段落
$doc.on('click', '.cell p.text', e => {
  const $p = $(e.target), $cell = $p.closest('.cell')
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

function _selectionChanged() {
  if (_status.down) { // 选择集改变消息连续触发时取最后的
    _status.tm = setTimeout(_selectionChanged, 50)
  } else {
    const sel = _getSelectedTexts()
    if (sel[1]) {
      document.getSelection().empty()
      $('p.active').removeClass('active')
      if (sel[2] === 'cross') {
        $('.selected').removeClass('selected')
        _showSelectedTip($(sel[1]))
        delete _status.lastClick
      } else if (sel[0]) {
        _clearOtherRowsSelected($(sel[1]))
        $('.selected', sel[1]).removeClass('selected') // 当前TR的其它列的选择不变
        sel[0].forEach(p => $(p).addClass('selected'))
        _showSelectedTip($(sel[1]))
        delete _status.lastClick
      }
    }
  }
}

// 在当前单元格拉选多个段落
$doc.on('selectionchange', () => {
  if (!$('.modal-open,.swal2-shown')[0]) {
    window.clearTimeout(_status.tm)
    _status.tm = setTimeout(_selectionChanged, 50)
  }
})

// 快捷键：回车移为一组
$doc.on('keyup', e => {
  const el = document.activeElement, tagName = el.tagName
  const isInput = /^(TEXTAREA|INPUT)/.test(tagName), inPopup = $('.swal2-show').length > 0
  let handled = false

  if (isInput && inPopup && editable && e.key === 'Enter' && !$(el).val().trim()) {
    $('.swal2-show .swal2-confirm').click()
    handled = true
  } else if (!isInput && !inPopup && editable) {
    handled = true
    if (e.key === 'Enter') {
      mergeRow()
    } else if (e.key === 'Escape') {
      $('.selected').removeClass('selected')
      $('p.active').removeClass('active')
    } else if (e.key.toUpperCase() === 'T') {
      _insertToc($('p.active').first())
    } else {
      handled = false
    }
  }
  if (handled) {
    e.stopPropagation()
    e.preventDefault()
  }
}).on('keydown', e => {
  if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
    _moveP($('.merged p.text.selected').first(), e.key === 'ArrowUp')
    e.stopPropagation()
    e.preventDefault()
  }
})

function _showSelectedTip($cell) {
  const $cs = $cell.closest('.columns').find('.cell')
  const colN = $cs.filter((i, c) => $('.selected', c).length > 0).length
  const showN = n => n > 1 ? `<b>${n}</b>` : `${n}`
  $cs.each((i, c) => {
    const $tip = $(`.sel-tip[data-i="${c.dataset.i}"]`), n = $('.selected', c).length
    $tip.toggle(n > 0).html(`选中 ${showN(n)} 段，共 ${showN(colN)} 栏`)
  })
}

const _menuEvents = { show: function() { this.hasClass('selected') || this.click() }}
const _ellipsis = (s, n=10) => s && s.length > n ? s.substring(0, n - 1) + '…' : s

// 段落的鼠标右键菜单
$.contextMenu({
  selector: '.original p.text:not(.del)',
  items: {
    splitP: {
      name: '拆分段落...',
      callback: function(){ _splitParagraph(this) },
    },
    mergeUp: {
      name: '合并到上段',
      callback: function(){ _mergeUp(this, false) },
      disabled: function(){ return !editable || !_mergeUp(this, true) },
    },
    tag: {
      name: '段落类型...',
      callback: function(){ _setTag(this) },
    },
    sep1: {name: '--'},
    moveUp: {
      name: '合并为一组<span class="key" title="回车键">Enter</span>',
      isHtmlName: true,
      callback: function(){ mergeRow(false) },
      disabled: function(){ return !editable || !mergeRow(true) },
    },
    sep2: {name: '--'},
    insertToc: {
      name: '插入科判条目...<span class="key">T</span>',
      isHtmlName: true,
      callback: function(){ _insertToc(this); },
      disabled: function(){ return !editable },
    },
    sep3: {name: '--'},
    markDel: {
      name: '标记删除',
      callback: function(){ _markDel(this) },
      disabled: function(){ return !editable },
    },
  },
  events: _menuEvents
})
$.contextMenu({
  selector: '.original p.text.del',
  items: {
    splitP: {
      name: '段落内容...',
      callback: function(){ _splitParagraph(this) },
    },
    insertToc: {
      name: '插入科判条目...<span class="key">T</span>',
      isHtmlName: true,
      callback: function(){ _insertToc(this); },
      disabled: function(){ return !editable },
    },
    sep1: {name: '--'},
    markDel: {
      name: '撤销删除标记',
      callback: function(){ _markDel(this) },
      disabled: function(){ return !editable },
    },
  },
  events: _menuEvents
})
$.contextMenu({
  selector: '.merged p.text',
  items: {
    splitP: {
      name: '拆分段落...',
      callback: function(){ _splitParagraph(this) },
    },
    mergeUp: {
      name: '合并到上段',
      callback: function(){ _mergeUp(this, false) },
      disabled: function(){ return !editable || !_mergeUp(this, true) },
    },
    tag: {
      name: '段落类型...',
      callback: function(){ _setTag(this) },
    },
    sep1: {name: '--'},
    moveUp: {
      name: '上移一组<span class="key" title="Alt键 + 上方向键">Alt+△</span>',
      isHtmlName: true,
      callback: function(){ _moveP(this, true, false) },
      disabled: function(){ return !editable || !_moveP(this, true, true) },
    },
    moveDown: {
      name: '下移一组<span class="key" title="Alt键 + 下方向键">Alt+▽</span>',
      isHtmlName: true,
      callback: function(){ _moveP(this, false, false) },
      disabled: function(){ return !editable || !_moveP(this, false, true) },
    },
    extractRow: {
      name: '另合为一组<span class="key" title="回车键">Enter</span>',
      isHtmlName: true,
      callback: function(){ mergeRow(false); },
      disabled: function(){ return !editable || !mergeRow(true)},
    },
    sep2: {name: '--'},
    insertToc: {
      name: '插入科判条目...<span class="key">T</span>',
      isHtmlName: true,
      callback: function(){ _insertToc(this); },
      disabled: function(){ return !editable },
    },
  },
  events: _menuEvents
})
$.contextMenu({
  selector: '.cell .toc_row,.toc-tree a',
  items: {
    edit: {
      name: '修改科判条目...',
      callback: function(){ _editTocRow(this) },
      disabled: function(){ return !editable },
    },
    sep1: {name: '--'},
    dis: {
      name: '断开关联',
      callback: function(){ _disLinkToc(this, false) },
      disabled: function(){ return !editable || !_disLinkToc(this, true) },
    },
    del: {
      name: '删除科判条目...',
      callback: function(){ _delTocRow(this) },
      disabled: function(){ return !editable },
    },
  },
  events: _menuEvents
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
    proj_id: getProjId()
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

// 对当前选中的一个段落进行内容拆分
function _splitParagraph($p) {
  const t0 = $p.text().trim(), del = $p.hasClass('del');
  (del || !editable ? Swal1 : Swal2).fire({
    title: `${del ? '段落内容' : '拆分段落'} <small>${$p.data('lineS')}</small>`,
    inputLabel: del ? '' : '在要拆分处插入分隔符“@”或回车换行，不能改字。',
    inputValue: t0,
    input: 'textarea',
    inputAttributes: {rows: 14},
    width: 650,
    draggable: true,
    confirmButtonText: '拆分',
    didOpen: () => activatePara($p),
    preConfirm: text => postApi('/proj/match/split',
      getParaInfo($p, {old_text: t0, text: text.trim()}),
      reloadWithSelected)
  })
}

function _insertToc($p) {
  const tip = '每行一个条目，行首可指定级别，或+-相对缩进\n' +
    '　例如 “2 二级”、“+ 子条目”、“-上级”、“条目 » 子条目”\n' +
    '“甲乙丙”等天干字开头可不指定级别，例如“丙二回答分”'
  const t = getCurrentTocNode(), tocText = _ellipsis(t.text)
  const data = getParaInfo($p, {toc: tocText && Object.assign({text: t.text}, t.data)})

  Swal2.fire({
    title: '插入科判条目',
    inputLabel: `插入到当前段落“${_ellipsis($p.text())}”前面。` +
        (tocText ? `\n不输入就关联到当前科判条目“${tocText}”，可直接按回车键。` : ''),
    input: 'textarea',
    inputAttributes: {rows: 3, placeholder: tip},
    width: 500,
    draggable: true,
    didOpen: () => activatePara($p, true),
    preConfirm: text => !text && !tocText ? false : postApi('/proj/match/toc/insert',
      {data: Object.assign(data, {text: text.trim()})}, r => r.add_toc ? reloadPage() : reloadWithSelected(r.data))
  })
}

function _getTocRowByTreeNode($r) {
  const $tree = $r.closest('.toc-tree')
  if ($tree[0])
    return getTocRowByTreeNode($r, $tree.closest('[data-ext]').data('ext'))
}

function _editTocRow($r) {
  const r = _getTocRowByTreeNode($r)
  const $p = r && r[1] || $r
  const info = r && r[0] ? r[0].data : getParaInfo($p, {level: $p.data('level'), text: $p.text()})

  activatePara($p, !r || !r[0])
  Swal2.fire({
    title: '修改科判条目',
    input: 'textarea',
    inputAttributes: {rows: 2},
    inputValue: `${info.level}  ${info.text}`,
    draggable: true,
    preConfirm: text => text && postApi('/proj/match/toc/edit',
      Object.assign({}, info, {text: text, proj_id: getProjId()}),
        r => reloadWithSelected(r.data))
  })
}

function _disLinkToc($r, test) {
  const r = _getTocRowByTreeNode($r)
  const $p = r && r[1] || $r

  if ($p.data('toc-id')) {
    if (!test) {
      const info = r && r[0] ? r[0].data : getParaInfo($p)
      postApi('/proj/match/toc/del',
      Object.assign({proj_id: getProjId(), dis_link: true}, info),
      res => $p.remove() && tocEnsureVisible(res.data))
    }
    return true
  }
}

function _delTocRow($r) {
  const r = _getTocRowByTreeNode($r)
  const $p = r && r[1] || $r
  const info = r && r[0] ? r[0].data : getParaInfo($p, {level: $p.data('level'), text: $p.text()})
  const node = r && r[0] || getTocNode(info.toc_id, info)

  activatePara($p, !r || !r[0])
  if (node && node.children.length) {
    return showError('不能删除', '需要先删除子条目')
  }
  Swal2.fire({
    title: '删除确认',
    text: `确实要删除科判条目“${ info.text }”？`,
    draggable: true,
    preConfirm: () => postApi('/proj/match/toc/del',
      Object.assign({proj_id: getProjId()}, info),
      res => $p.remove() && tocEnsureVisible(res.data, true)),
  })
}

// 对当前单元格内选中的段落设置段落类型
function _setTag($p) {
  const $s = $p.closest('.cell').find('.selected')
  const sel = $s.get().map(p => getParaInfo($(p)))
  const tags = window.tags || {}, used = Object.keys(tags).filter(s => $p.hasClass(s));

  (editable ? Swal2 : Swal1).fire({
    title: '段落类型',
    input: 'select',
    inputOptions: tags,
    inputValue: used[0],
    inputPlaceholder: '选择一种段落类型',
    draggable: true,
    confirmButtonText: '设置',
    didOpen: () => activatePara($p),
    preConfirm: v => !v || used[0] === v ? false : postApi('/proj/match/tag',
      {data: {info: getParaInfo($p, {tag: v}), sel: sel}},
      reloadWithSelected)
  })
}

// 对当前单元格内选中的多个段落切换是否标记删除
function _markDel($p) {
  const $s = $p.closest('.cell').find('.selected')
  const sel = $s.get().map(p => getParaInfo($(p)))
  postApi('/proj/match/mark-del', {data: sel}, reloadWithSelected)
}

// 将当前选中的一个段落合并到上一段
function _mergeUp($p, test) {
  const $prev = $p.prev('.p-head').prev('.text:not(.del)')
  if ($prev[0]) {
    if (!test) {
      const info = getParaInfo($p), prev = getParaInfo($prev)
      postApi('/proj/match/merge', {data: {info: info, prev: prev}},
        () => reloadWithSelected($p[0]))
    }
    return true
  }
}

// 将当前单元格内选中的多个段落移到相邻行的单元格内，可下移到未合并区
function _moveP($p, up, test) {
  const $col = $p.closest('.merged .cell'), $lines = $col.find('p.text')
  const $sel = $col.find('.selected:not(.del)')

  if (up ? $lines[0] === $sel[0] : $lines.last()[0] === $sel.last()[0]) {
    const $tr = $p.closest('.merged'), $trTo = up ? $tr.prev('.merged') : $tr.next('.merged')
    if ($trTo[0] || !up) {
      if (!test) {
        const rows = $sel.get().map(p => getParaInfo($(p)))
        postApi('/proj/match/move', {data: {
          up: up, from_row: parseInt($tr.data('row-i')),
          to_row: parseInt($trTo.data('row-i')), sel: rows}}, reloadWithSelected)
      }
      return true
    }
  }
}

// 将各栏的选中段落合并为一组对照
function mergeRow(test=false) {
  const $tr = $('.selected').closest('.columns').first()
  const $sel = $tr.find('.selected:not(.del)')

  if ($tr.find('.cell').length < 2) { // 单栏不能合并对照
    return false
  }
  if ($tr.hasClass('merged') && $sel.length === $tr.find('.text:not(.del)').length) {
    return false
  }
  if ($sel.length < 1) {
    return !test && showError('移为一组', '在各栏中依次选择要同组的段落，然后重试。')
  }
  if (test) {
    return true
  }
  const warnCol = [], warnP = []
  const data = {columns: {}, rows: [], proj_id: getProjId()}

  $tr.find('.cell').each((i, col) => {
    data.columns[i] = $('.selected.text:not(.del)', col).map((j, p) => {
      const row = getParaInfo($(p))
      data.rows.push(row)
      row['text'] = $(p).text().substring(0, 10)
      return row
    }).get()
    if ($tr.hasClass('original')) {
      _checkNotSelectFirstP(i, col, data, warnCol, warnP)
    }
  })

  const onSuccess = () => reloadWithSelected(true)
  if (warnCol.length) {
    Swal2.fire({
      title: '确认上移',
      text: `第 ${warnCol.join('、')} 栏没有选中第一段(红字)，会导致内容顺序与原文不一致。确实要合并为一组吗？`,
      draggable: true,
      didOpen: () => { $(warnP).addClass('error') },
      didClose: () => { $(warnP).removeClass('error') },
      preConfirm: () => postApi('/proj/match/merge-row', {data: data}, onSuccess)
    })
  } else {
    if ($tr.hasClass('merged')) {
      data.from_row = parseInt($tr.data('row-i'))
    }
    postApi('/proj/match/merge-row', {data: data}, onSuccess)
  }
}

function _checkNotSelectFirstP(i, col, data, warnCol, warnP) {
  let p = col.firstChild
  for (; p && !$(p).hasClass('text'); p = p.nextSibling) {} // 找到第一段
  if ($(p).hasClass('text') && !p.classList.contains('selected') // 第一段未选中、未标记删除
      && !p.classList.contains('del') && data.columns[i].length) { // 此栏选中了其他段落
    warnCol.push(`${i+1}`)
    for (; p; p = p.nextSibling) {
      if ($(p).hasClass('text') && !p.classList.contains('del')) {
        if (p.classList.contains('selected'))
          break
        warnP.push(p)
      }
    }
  }
}

function onPageLoaded() {
  $('.cell .sec').each((i, sec) => {
    const t = $(sec).closest('.cell').find(`.text[data-s-i="${sec.dataset.sI}"]`)
    if (t.length < 1) {
      sec.remove()
    }
  })
  $('.merged:not([data-row-i="1"]) .col-name,.single-article .col-name,.p-head.xu_first').remove()
}

$('.alert .close').click(function(){
  options['matchTip'] = 'hide'
  saveOptions()
  $('.toggle-alert').removeClass('active')
})
$('.toggle-alert').click(function(){
  $('.toggle-alert').toggleClass('active', options['matchTip'] === 'hide')
  if (options['matchTip'] === 'hide') {
    delete options['matchTip']
    saveOptions()
    reloadPage()
  } else {
    options['matchTip'] = 'hide'
    saveOptions()
    $('.alert').alert('close')
  }
})

$(function () {
  onPageLoaded()
  if (window.options && options['matchTip'] === 'hide') {
    $('.alert').alert('close')
  } else {
    $('.toggle-alert').addClass('active')
  }

  const proj_id = getProjId()
  for (let i = 0; i < 12; i++) {
    if (options.proj_id !== proj_id) {
      delete options[`hide-col-${i}`]
    } else if (options[`hide-col-${i}`]) {
      $('.columns-p').toggleClass(`hide-col-${i}`)
      $(`.toggle-col[data-i="${i}"]`).toggleClass('active')
    }
  }
  if (options.proj_id !== proj_id) {
    options.proj_id = proj_id
    saveOptions()
  }
})

function reloadWithSelected(onlyFirst=false) {
  const $sel = $('.selected.text')
  const lastSelected = (onlyFirst instanceof HTMLElement ? $(onlyFirst) :
    onlyFirst === true ? $sel.first() : $sel).get().map(p => [p.dataset.sId, p.dataset.line])

  renderApi(html => {
    $('table').html(html)
    onPageLoaded()
    lastSelected.forEach(s => {
      $(`.text[data-s-id="${s[0]}"][data-line="${s[1]}"]`).addClass('selected')
    })
    if (window.scrollParaToVisible) {
      scrollParaToVisible($('p.selected'))
    }
    if (onlyFirst && onlyFirst.toc_id) {
      tocEnsureVisible(onlyFirst, true)
    }
  })
}
