/**
 * 选中一个段落
 * @param {HTMLElement} p
 * @private
 */
function _selectCellP(p) {
  const nodes = [], cell = p.closest('.cell')
  scanNodesToSel(p.firstChild, p.lastChild, cell, nodes)
  const n = selNodes(nodes, p.firstChild, p.lastChild, 0, -1)
  selNodesEnd(cell, n)
}

function _selectCellRange() {
  const sel = document.getSelection()
  const first = sel.rangeCount && sel.getRangeAt(0).startContainer
  const cell = first ? $(first).closest('.cell')[0] : null
  let n = 0

  for (let ri = 0; cell && ri < sel.rangeCount; ri++) {
    const r = sel.getRangeAt(ri), nodes = []
    let startContainer = r.startContainer, endContainer = r.endContainer
    let startOffset = r.startOffset, endOffset = r.endOffset

    while (startContainer['closest']) {
      startContainer = startContainer.firstChild
      startOffset = 0
    }
    while (endContainer['closest']) {
      endContainer = endContainer.lastChild
      endOffset = endContainer.textContent.length
    }

    scanNodesToSel(startContainer, endContainer, cell, nodes)
    n += selNodes(nodes, startContainer, endContainer, startOffset, endOffset)
  }
  selNodesEnd(cell, n)
}

function _endBusy() {
  setTimeout(() => delete _status.busy, 50)
}

// 点击段落设置选中状态
function clickCellP($p, e) {
  const s = getSelectedTexts(e.shiftKey && e.target, true)
  _status.busy = true
  if (s[2] === 'cross') { // 跨栏选择就清除选择
    clearAllSelected()
  } else { // 点击就选择当前整个段落
    const len = $p.find('.selected').get().reduce((a, c) => a + c.textContent.length, 0)
    if (!e.shiftKey) {
      clearSelectedInCell($p.closest('.cell'))
    }
    const $used = $(e.target).closest('.cell-r .used')
    if ($used[0] && !$('.hi', e.target)[0]) {
      highLightNote($used.attr('data-nid'))
      const $hi = $('.cell-l .hi')
      scrollToVisible(document.querySelector('.cell-l'), $hi.first(), $hi.last())
    } else if (len !== $p.text().length) {
      _selectCellP($p[0])
    }
  }
  showSelectedTip($p.closest('.cell'))
  _endBusy()
  window.clearTimeout(_status.tmSel)
  e.stopPropagation()
  e.preventDefault()
}

function _selectionChanged(e) {
  if (_status.down) { // 选择集改变消息连续触发时取最后的
    _status.tmSel = setTimeout(() => _selectionChanged(e), 50)
  } else {
    const sel = getSelectedTexts(e.shiftKey && e.target, true)
    if (sel[1]) {
      _status.busy = true
      if (sel[2] === 'cross') { // 跨栏选择就清除选择
        clearAllSelected()
        showSelectedTip($(sel[1]))
      } else if (sel[0]) { // 按范围选择文本
        _selectCellRange()
        showSelectedTip($(sel[1]))
      }
      delete _status.lastClick
      _endBusy()
    }
  }
}

// 在当前单元格拉选多个段落
$doc.on('selectionchange', (e) => {
  if (!inModal() && !_status.busy && _status.down) {
    window.clearTimeout(_status.tmSel)
    _status.tmSel = setTimeout(() => _selectionChanged(e), 50)
  }
})

$doc.on('keyup', e => {
  const el = document.activeElement, tagName = el.tagName
  const isInput = /^(TEXTAREA|INPUT)/.test(tagName), inPopup = $('.swal2-show').length > 0
  let handled = false

  if (!isInput && !inPopup) {
    handled = true
    if (e.key === 'Enter') {
      _mergeNote()
    } else if (e.key === 'Escape') {
      const $c = $('p.active').closest('.cell')
      clearAllSelected($c.hasClass('cell-l') ? '.cell-l' : $c.hasClass('cell-r') ? '.cell-r' : '')
      showSelectedTip($('.cell-r'))
      window.clearTimeout(_status.tmSel)
    } else {
      handled = false
    }
  }
  if (handled) {
    e.stopPropagation()
    e.preventDefault()
  }
})

function showSelectedTip($cell) {
  const $tip = $cell.find('.sel-tip')
  if ($tip[0]) {
    const showN = n => n > 1 ? `<b>${n}</b>` : `${n}`
    const pn = $cell.find('p:has(.selected)').length
    $tip.show().html(`选中 ${showN(pn)} 段`)
    $('.app').toggleClass('has-sel-tip', $('.sel-tip:visible').length > 0)
  }
}

function _selPos(cellCls) {
  const $allP = $(`${'.cell' + cellCls} p:has(.selected)`)
  return $allP.map((i, p) => {
    const $p = $(p), $sel = $('.selected', p), allText = $p.text()

    $sel.each((j, s) => {
      const html = s.innerHTML
      s.textContent = '\x02'
      const pText = $p.text(), pos = pText.indexOf('\x02'),
        startT = pText.substring(0, pos), endT = pText.substring(pos + 1),
        i0 = startT.length, i1 = allText.length - endT.length
      $(s).attr('i0', i0).attr('i1', i1).html(html)
    })

    const i0 = parseInt($sel.first().attr('i0')), i1 = parseInt($sel.last().attr('i1')),
      ret = {
        i0: i0, i1: i1, len: 0,
        all: i0 === 0 && i1 === allText.length ? 1 : 0,
        line: parseInt($p.data('line')),
        s_id: $p.data('s-id')
      }

    $p.toggleClass('all-sel', ret.all === 1)
    if (ret.all) {
      if (i === 0 || i === $allP.length - 1) {
        ret.text = allText.substring(0, 8)
        ret.len = allText.length
      }
    } else {
      delete ret.all
      ret.sel = $sel.map((j, s) => {
        const $s = $(s), i0 = parseInt($s.attr('i0')), i1 = parseInt($s.attr('i1')),
           text = allText.substring(i0, i1)
        ret.len += text.length
        return {
          i0: i0, i1: i1, len: text.length,
          text: text.substring(0, 6)}
      }).get()
    }
    return ret
  }).get()
}

function _getLeftText(note) {
  const texts = []
  selectPText($('.cell-l'), note.left, (text) => texts.push(text))
  return texts.join(' ')
}

function _addNoteForSelected(note, data, $l, $r) {
  const onSuccess = r => {
    note.id = r && r.id || note.id
    addNote(note, $l, $r, $('.cell-r p:has(.selected)'))
    clearAllSelected()
    window.notes.push(note)
    setTimeout(() => {
      $(`.note-tag[data-nid="${note.id}"]`).addClass('active')
      reorderNoteTags()
    }, 20)
  };

  if (!editable) onSuccess()
  return postApi('/proj/note/add', {data: data}, onSuccess)
}

function _mergeNote(freeNode) {
  const pL = _selPos('.cell-l'), pR = _selPos('.cell-r'),
    $l = $('.cell-l .selected'), $r = $('.cell-r .selected')

  if (nA.notes || freeNode) {
    if (!pL.length) return showError('不能添加', '请选择要关联注解的文本。')
    const leftText = ellipsisText(_getLeftText({left: pL}), 20)
    Swal2.fire({
      title: '添加注解',
      html: `
<label for="note-text" class="swal2-input-label">为“${leftText}”添加注解。</label>
<textarea id="note-text" rows="8" class="swal2-textarea" maxlength="2000" style="width: 100%; margin: .5em 0 5px;"></textarea>
<input id="note-source" class="swal2-input" maxlength="40" placeholder="来源" style="width: 100%; margin: 0;">`,
      focusConfirm: false,
      width: 500,
      backdrop: false,
      preConfirm: () => {
        const text = $('#note-text').val().trim(),
          source = $('#note-source').val().trim(),
          inline = text.indexOf('\n') < 0 && pL[0].len <= 40 && text.length <= 200;
        if (!text) { $('#note-text').focus(); return false }
        if (!source) { $('#note-source').focus(); return false }
        const note = {id: `${1 + window.notes.length}`, left: pL, right: [],
          inline: pL.length === 1 && inline ? 1 : 0,
          note: {text: text, source: source}}
        const data = {proj_id: getProjId(), leftAid: nA['note_for'] || nA._id, noteAid: '', note: note}
        return _addNoteForSelected(note, data, $l, note.note)
      },
    })
  } else if (pL.length && pR.length) {
    const inline = pL.length === 1 && pR.length === 1 && pL[0].len <= 40 && pR[0].len <= 200
    const note = {id: `${1 + window.notes.length}`, left: pL, right: pR, inline: inline ? 1 : 0}
    const data = {proj_id: getProjId(), noteAid: nA._id, leftAid: nA['note_for'], note: note}
    _addNoteForSelected(note, data, $l, $r)
  } else showError('不能添加', '请在左右栏分别选择要关联注解的文本。')
}

function _removeAllNote() {
  Swal2.fire({
      title: '删除确认',
      html: `确实要删除 ${notes.length} 条注解？<br>删除后无法撤销，可提前导出备份。`,
      preConfirm: () => postApi('/proj/note/del',
        {data: {proj_id: getProjId(), all: true, note_a: nA}},
        () => reloadNotes([])),
    })
}

// 根据段落或注解标记删除注解
function _removeNote($p, test) {
  const nid = $p.closest('[data-nid]').attr('data-nid'),
    note = getNote(nid), $tag = $(`.note-tag[data-nid="${nid}"]`)

  if ($tag[0] && note && !$tag.hasClass('disabled')) {
    if (test) return true
    const st = getComputedStyle($tag[0], '::before')
    const text = _getLeftText(note)

    Swal2.fire({
      title: '删除确认',
      html: `确实要删除注解${st.content.replace(/"/g, '')}？<br>原文 “${ellipsisText(text, 16)}” 将恢复为未被注解的状态。`,
      draggable: true,
      preConfirm: () => postApi('/proj/note/del',
        {data: {proj_id: getProjId(), nid: nid, note_a: nA}},
        r => reloadNotes(r.data.notes)),
    })
  }
}
function _changeNote($p, test) {
  const nid = $p.closest('[data-nid]').attr('data-nid'),
    note = getNote(nid), $tag = $(`.note-tag[data-nid="${nid}"]`)

  if ($tag[0] && note && !$tag.hasClass('disabled')) {
    if (test) return true
    const st = getComputedStyle($tag[0], '::before')
    const text = _getLeftText(note)

    Swal2.fire({
      title: `修改${st.content.replace(/"/g, '')}注解类型`,
      inputLabel: `原文：${ellipsisText(text, 20)}`,
      input: 'select',
      inputOptions: {inline: '行间注', end: '段尾注', front: '段前注'},
      inputValue: note.type || (note.inline ? 'inline' : 'end'),
      draggable: true,
      preConfirm: value => postApi('/proj/note/type',
        {data: {proj_id: getProjId(), nid: nid, type: value, note_a: nA}},
        r => reloadNotes(r.data.notes)),
    })
  }
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
    preConfirm: text => postApi('/proj/match/split',
      getParaInfo($p, {old_text: t0, text: text.trim()}), reloadPage)
  })
}

// 将当前选中的一个段落合并到上一段
function _mergeUp($p, test) {
  const $prev = $p.prev('.text:not(.del)')
  if ($prev[0]) {
    if (!test) {
      const info = getParaInfo($p), prev = getParaInfo($prev)
      postApi('/proj/match/merge', {data: {info: info, prev: prev}}, reloadPage)
    }
    return true
  }
}

// 对当前单元格内选中的段落设置段落类型
function _setTag($p) {
  const $s = $p.closest('.cell').find('.selected')
  const sel = $s.get().map(p => getParaInfo($(p)))
  const tags = window.p_tags || {}, used = Object.keys(tags).filter(s => $p.hasClass(s));

  (editable ? Swal2 : Swal1).fire({
    title: '段落类型',
    input: 'select',
    inputOptions: tags,
    inputValue: used[0],
    inputPlaceholder: '选择一种段落类型',
    inputLabel: `段落 “${ellipsisText($p.text(), 24)}”`,
    draggable: true,
    confirmButtonText: '设置',
    didOpen: () => activatePara($p),
    preConfirm: v => !v || used[0] === v ? false : postApi('/proj/match/tag',
      {data: {info: getParaInfo($p, {tag: v}), sel: sel}}, reloadPage)
  })
}

$.contextMenu({
  selector: '.cell-r [data-nid]',
  items: {
    removeNote: {
      name: '删除注解...',
      isHtmlName: true,
      callback: function(){ _removeNote(this, false); },
      disabled: function(){ return !_removeNote(this, true); },
    },
  }
})
$.contextMenu({
  selector: '.note-tag,.note-row-head,.note-row-end',
  items: {
    changeNote: {
      name: '注解类型...',
      callback: function(){ _changeNote(this, false); },
      disabled: function(){ return !_changeNote(this, true); },
    },
    sep1: {name: '--'},
    removeNote: {
      name: '删除注解...',
      callback: function(){ _removeNote(this, false); },
      disabled: function(){ return !_removeNote(this, true); },
    },
    sep2: {name: '--'},
    removeAllNote: {
      name: '删除所有注解...',
      callback: function(){ _removeAllNote(); },
      disabled: function(){ return !editable || !window.notes.length || $('.note-tag.disabled')[0]; },
    },
  }
})
$.contextMenu({
  selector: 'p.text',
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
    mergeNote: {
      name: (nA.notes ? '添加注解...' : '左右选择为注解') + '<span class="key" title="回车键">Enter</span>',
      isHtmlName: true,
      callback: function(){ _mergeNote() },
    },
    addNote: nA.notes ? {} : {
      name: '添加注解...',
      callback: function(){ _mergeNote(true) },
    },
  }
})

function onPageLoaded() {
  _status.autoSaveOpt = _status.editMode = true
  $('.cell .sec').each((i, sec) => {
    const t = $(sec).closest('.cell').find(`.text[data-s-i="${sec.dataset.sI}"]`)
    if (t.length < 1) {
      sec.remove()
    }
  })
  $('.col-name,.p-head').remove()
  $('.cell-l .text').removeClass('ellipsis-n')
  reloadNotes(null)
  setTimeout(() => $('#expand-all').click(), 50)
}

$('.alert .close').click(function(){
  options['noteTip'] = 'hide'
  saveOptions()
  $('.toggle-alert').removeClass('active')
})
$('.toggle-alert').click(function(){
  $('.toggle-alert').toggleClass('active', options['noteTip'] === 'hide')
  if (options['noteTip'] === 'hide') {
    delete options['noteTip']
    saveOptions()
    reloadPage()
  } else {
    options['noteTip'] = 'hide'
    saveOptions()
    $('.alert').alert('close')
  }
})

$(function () {
  onPageLoaded()
  if (window.options && options['noteTip'] === 'hide') {
    $('.alert').alert('close')
  } else {
    $('.toggle-alert').addClass('active')
  }
})
