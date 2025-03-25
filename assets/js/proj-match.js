// 清除其他TR的段落选择
function clearOtherRowsSelected($p) {
  const ri = $p.closest('.columns').data('row-i')
  $(`.columns:not([data-row-i="${ri}"]) .selected`).removeClass('selected')
}

// 点击段落设置选中状态
function clickCellP($p, e) {
  const $cell = $p.closest('.cell')
  const oldSel = $('.selected'), oldIsSel = $p.hasClass('selected')
  const sel_ = getSelectedTexts(e.shiftKey && e.target)
  const sel = sel_[0] || [] // 当前单元格的选中段落

  document.getSelection().empty()
  clearOtherRowsSelected($p)
  $cell.find('.selected').removeClass('selected') // 当前TR的其它列的选择不变

  if (e.shiftKey) {
    sel.forEach(p => $(p).addClass('selected'))
  } else if (!oldIsSel || oldSel.length !== 1 || (sel.length === 1 && sel[0] !== e.target)) {
    $p.addClass('selected')
  } // else: toggle selected
  showSelectedTip($cell)
}

function _selectionChanged() {
  if (_status.down) { // 选择集改变消息连续触发时取最后的
    _status.tmSel = setTimeout(_selectionChanged, 50)
  } else {
    const sel = getSelectedTexts()
    if (sel[1]) {
      document.getSelection().empty()
      $('p.active').removeClass('active')
      if (sel[2] === 'cross') {
        $('.selected').removeClass('selected')
        showSelectedTip($(sel[1]))
        delete _status.lastClick
      } else if (sel[0]) {
        clearOtherRowsSelected($(sel[1]))
        $('.selected', sel[1]).removeClass('selected') // 当前TR的其它列的选择不变
        sel[0].forEach(p => $(p).addClass('selected'))
        showSelectedTip($(sel[1]))
        delete _status.lastClick
      }
    }
  }
}

// 在当前单元格拉选多个段落
$doc.on('selectionchange', () => {
  if (!inModal()) {
    window.clearTimeout(_status.tmSel)
    _status.tmSel = setTimeout(_selectionChanged, 50)
  }
})

// 快捷键：回车移为一组，Esc清除选择
$doc.on('keyup', e => {
  const el = document.activeElement, tagName = el.tagName
  const isInput = /^(TEXTAREA|INPUT)/.test(tagName), inPopup = $('.swal2-show').length > 0
  let handled = false

  if (isInput && inPopup && editable && e.key === 'Enter' && !$(el).val().trim()) {
    $('.swal2-show .swal2-confirm').click()
    handled = true
  } else if (!isInput && !inPopup) {
    handled = true
    if (e.key === 'Enter' && editable) {
      mergeRow()
    } else if (e.key === 'Escape') {
      $('.selected').removeClass('selected')
      $('p.active').removeClass('active')
      showSelectedTip($('.cell:first-child'))
    } else if (e.key.toUpperCase() === 'T') {
      _insertToc($('p.active').first())
    } else if (e.key === '-' || e.key === '=') {
      e.key === '-' ? reduceFont() : enlargeFont()
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

function showSelectedTip($cell) {
  const $cs = $cell.closest('.columns').find('.cell')
  const colN = $cs.filter((i, c) => $('.selected', c).length > 0).length
  const showN = n => n > 1 ? `<b>${n}</b>` : `${n}`
  const $lastTip = $('.sel-tip:visible').first()

  $cs.each((i, c) => {
    const $tip = $(`.sel-tip[data-i="${c.dataset.i}"]`), n = $('.selected', c).length
    $tip.toggle(n > 0).html(`选中 ${showN(n)} 段，共 ${showN(colN)} 栏`)
  })
  if ($('.sel-tip:visible').length < 1) {
    $lastTip.show()
  }
  $('.app').toggleClass('has-sel-tip', $('.sel-tip:visible').length > 0)
}

window.activatePara = function($p, selectTocNode=false) {
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
  window.clearTimeout(_status.tmSel)
}

const _menuEvents = { show: function() { this.hasClass('selected') || this.click() }}

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
      disabled: function(){ return !editable || _status.oneCol || !mergeRow(true) },
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

// 对当前选中的一个段落进行内容拆分
function _splitParagraph($p) {
  const t0 = $p.text().trim(), del = $p.hasClass('del');
  (del || !editable ? Swal1 : Swal2).fire({
    title: `${del ? '段落内容' : '拆分段落'} <small>${$p.data('lineS')}</small>`,
    inputLabel: del ? '' : '在要拆分处插入分隔符“@”或回车换行，不能改字。',
    inputValue: t0,
    input: 'textarea',
    inputAttributes: {rows: 14},
    width: 800,
    confirmButtonText: '拆分',
    didOpen: () => activatePara($p),
    preConfirm: text => postApi('/proj/match/split',
      getParaInfo($p, {old_text: t0, text: text.trim()}),
      reloadWithSelected)
  })
}

function _insertToc($p) {
  const tip = '每行一个条目，行首可指定级别数字，或+-相对缩进\n' +
    '　例如 “2 二级”、“+ 子条目”、“-上级”、“条目 » 子条目”\n' +
    '“甲乙丙”等天干地支开头可不指定级别数字，例如“丙二回答分”'
  const t = getCurrentTocNode(), tocText = ellipsisText(t.text)
  const data = getParaInfo($p, {toc: tocText && Object.assign({text: t.text}, t.data)})

  Swal2.fire({
    title: '插入科判条目',
    inputLabel: `插入到当前段落“${ellipsisText($p.text())}”前面。` +
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
  const childN = node && node.children_d.length

  activatePara($p, !r || !r[0])
  if (childN) {
    info.children = node.children_d.map(s => parseInt(s.replace('toc-', '')))
  }
  Swal2.fire({
    title: '删除确认',
    text: `确实要删除科判条目“${ellipsisText(info.text, 12)}”${childN ? '及' + childN + '个子条目' : ''}？`,
    draggable: true,
    preConfirm: () => postApi('/proj/match/toc/del',
      {data: Object.assign({proj_id: getProjId()}, info)},
      res => $p.remove() && tocEnsureVisible(res.data, true)),
  })
}

// 对当前单元格内选中的段落设置段落类型
function _setTag($p) {
  const $s = $p.closest('.cell').find('.selected')
  const sel = $s.get().map(p => getParaInfo($(p)))
  const pText = ellipsisText($p.text(), sel.length > 1 ? 20 : 24)
  const ts = window.p_tags || {}, used = Object.keys(ts).filter(s => $p.hasClass(s))
  const tags = Object.entries(ts).map(v => [v[0], v[1].replace('*', sel.length > 1 ? ' 批量' : '')]);

  (editable ? Swal2 : Swal1).fire({
    title: '段落类型',
    input: 'select',
    inputOptions: Object.fromEntries(tags),
    inputValue: used[0],
    inputPlaceholder: '选择一种段落类型',
    inputLabel: `段落 “${pText}”${sel.length > 1 ? '等' + sel.length + '个段落' : ''}`,
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

  if (_status.oneCol || $tr.find('.cell').length < 2) { // 单栏不能合并对照
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
  _status.autoSaveOpt = _status.editMode = true
  $('.cell .sec').each((i, sec) => {
    const t = $(sec).closest('.cell').find(`.text[data-s-i="${sec.dataset.sI}"]`)
    if (t.length < 1) {
      sec.remove()
    }
  })
  $('.merged:not([data-row-i="1"]) .col-name,.single-article .col-name,' +
    '.p-head.xu_first,.p-head[data-tag="卷"],.p-head[data-tag="节"]').remove()
  if (!editable) {
    showError('只读提示', '需要登录，且是创建者或协编才能修改。')
  }
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

// 科判树的鼠标右键菜单
$.contextMenu({
  selector: '.drop-toc-name',
  items: {
    edit: {
      name: '修改科判名称...',
      callback: function(){ _editTocName(this) },
      disabled: function(){ return !editable },
    },
    add: {
      name: '导入新的科判...',
      callback: function(){ importToc(this) },
      disabled: function(){ return !editable },
    },
    addHtml: {
      name: '从CBeta网页导入科判...',
      callback: function(){ importTocHtml(this) },
      disabled: function(){ return !editable },
    },
    sep1: {name: '--'},
    export: {
      name: '导出科判',
      callback: function(){ _exportToc(this) },
    },
    sep2: {name: '--'},
    del: {
      name: '删除科判...',
      callback: function(){ _delToc(this) },
      disabled: function(){ return !editable },
    },
  }
})

function importToc(title, toc_text) {
  const $a = $('.cell p.active,.single-article p.text').first()
  const a_id = $a[0] ? $a.closest('.cell').data('id') : ''
  const $c = $(`.cell[data-id="${a_id}"] .col-name`).first()
  const $p = $a[0] ? $a : $(`.cell[data-id="${a_id}"] p`).first()
  const label = $c[0] && `<label for="t-title" class="swal2-input-label m-t-0 m-b-10">为经典“${ $c.text()}”增加科判</label>`
  const tip = `每行一个科判条目，例如 “2 二级”、“  - 次辨题名”
以天干地支开头可不指定级别数字，例如“丙二回答分”
如需从CBeta科判网页导入，请用“导入科判网页”功能`

  if (!a_id) {
    return showError('不能导入', '请在对应栏中点击段落，然后再试。')
  }
  Swal2.fire({
    title: '导入科判',
    width: 600,
    html: `${label || ''}
<input id="t-title" class="swal2-input" maxlength="30" placeholder="科判名称" value="${title || ''}"
  style="width: 100%; margin: 0;">
<label for="t-text" class="swal2-input-label">每行一个科判条目，行首可指定级别数字，或+-相对缩进</label>
<textarea id="t-text" rows="10" class="swal2-textarea" maxlength="2000"
 placeholder="${tip}" style="width: 100%; margin: .5em 0 5px;">${toc_text || ''}</textarea>`,
    focusConfirm: !!title,
    preConfirm: () => {
      const name = $('#t-title').val().trim(), text = $('#t-text').val().trim();
      if (!name) { $('#t-title').focus(); return false }
      if (!text) { $('#t-text').focus(); return false }
      return postApi('/proj/match/toc/import',
        getParaInfo($p, {name: name, text: text}), reloadPage)
    }
  })
}

function importTocHtml() {
  const $a = $('.cell p.active,.single-article p.text').first()
  const a_id = $a[0] ? $a.closest('.cell').data('id') : ''
  const $c = $(`.cell[data-id="${a_id}"] .col-name`).first()
  const label = ($c[0] ? `为经典“${ $c.text()}”增加科判，` : '') + '请选择从CBeta科判页面下载(汇出)的网页文件。'

  if (!a_id) {
    return showError('不能导入', '请在对应栏中点击段落，然后再试。')
  }
  Swal2.fire({
    title: '导入科判',
    input: 'file',
    inputLabel: label,
    inputAttributes: {'accept': 'text/html'},
    preConfirm: file => {
      if (!file) return false
      const formData = new FormData()
      formData.append('file', file)
      return postApi('/proj/import/toc_cb', formData, res => {
        if (Array.isArray(res.toc)) {
          importToc(res.title, res.toc.map(t => `${'  '.repeat(t.level - 1)}- ${t.level} ${t.text}`).join('\n'))
        }
      })
    }
  })
}

function _exportToc($s) {
  const ext = $s.closest('[data-ext]').data('ext')
  const $t = _$tree[ext], a_id = $t.attr('data-a-id'), ti = $t.attr('data-toc-i')
  getApi(`/proj/toc/${a_id}/${ti}`, res => {
    const d = res.data, rows = d.rows, content = [d.name]
    _scanTocRows(ext, rows)
    rows.forEach(r => content.push(`${'  '.repeat(r.level - 1)}- ${r.level} ${r.text}`))
    download(content.join('\n'), d.code + '-md.txt')
  })
}

function _delToc($s) {
  const ext = $s.closest('[data-ext]').data('ext')
  const $t = _$tree[ext], a_id = $t.attr('data-a-id'), ti = $t.attr('data-toc-i')
  const $p = $(`.cell[data-id="${a_id}"] p[data-line]`).first()
  Swal2.fire({
    title: '删除确认',
    text: `确实要删除“${ $s.text()}”的全部科判条目？`,
    preConfirm: text => text && postApi('/proj/match/toc/del',
      getParaInfo($p, {del_root: true, toc_i: ti}), reloadPage)
  })
}

function _editTocName($s) {
  const ext = $s.closest('[data-ext]').data('ext')
  const $t = _$tree[ext], a_id = $t.attr('data-a-id'), ti = $t.attr('data-toc-i')
  const $p = $(`.cell[data-id="${a_id}"] p[data-line]`).first()
  const $c = $(`.cell[data-id="${a_id}"] .col-name`).first()

  Swal2.fire({
    title: '修改科判名称',
    inputLabel: $c.text() ? `修改经典“${ $c.text()}”的科判名称` : '',
    input: 'text',
    inputValue: $s.text(),
    preConfirm: text => text && postApi('/proj/match/toc/edit',
      getParaInfo($p, {edit_root: true, toc_i: ti, text: text}), reloadPage)
  })
}
