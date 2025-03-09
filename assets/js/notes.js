const nA = window.nA || {}

/**
 * 打散一个节点
 * @param {HTMLElement} el
 * @private
 */
function _unwrapNode(el) {
  const f = document.createDocumentFragment()
  Array.from(el.childNodes).forEach(c => f.append(c))
  el.replaceWith(f)
}

/**
 * 重置一栏的选中状态、注解展开状态
 * @param {jQuery} $cell 栏元素
 * @private
 */
function clearSelectedInCell($cell) {
  $cell.find('p.has-sel').removeClass('has-sel')
  $cell.find('.active').removeClass('active')
  $cell.find('.note-tag.expanded').removeClass('expanded')
  $cell.find('.note-p').removeClass('expanded')
  unwrapSelected($cell)
  unwrapSelected($('.cell'), 'hi')
  document.getSelection().empty()
}

/**
 * 打散所有选择的节点
 * @param {jQuery} $cell 栏元素
 * @param {string} [cls] 样式名
 * @private
 */
function unwrapSelected($cell, cls='selected') {
  const paras = [], $sel = $cell.find('.' + cls)
  $sel.each((i, s) => {
    const p = $(s).closest('p')[0]
    if (paras.indexOf(p) < 0) {
      paras.push(p)
    }
    _unwrapNode(s)
  })
  _flatten(paras)
}

/**
 * 清除所有栏的选中状态
 * @param {string} [cellCls] 是否限定只清除指定栏类名的栏
 * @private
 */
function clearAllSelected(cellCls='') {
  $('.cell' + cellCls).each((i, c) => clearSelectedInCell($(c)))
}

/**
 * 对多个段落整理零散的文本片段
 * @param {HTMLElement[]} paras
 * @private
 */
function _flatten(paras) {
  paras.forEach(p => {
    const $p = $(p)
    $p.find('.selected .selected').each((i, s) => _unwrapNode(s))
    const arr = $p.find('.selected').get()
    for (let i = arr.length - 1; i >= 0; i--) {
      const s = arr[i], prev = s.previousSibling
      if (prev && prev.append && prev.classList.contains('selected')) {
        Array.from(s.childNodes).forEach(c => prev.append && prev.append(c))
        prev.dataset.id = '' + Math.max(parseInt(prev.dataset.id), parseInt(s.dataset.id))
        s.remove()
      }
    }
    if (!$p.hasClass('has-sel') && arr.length) {
      $p.addClass('has-sel')
    }
    $p.html($p.html())
  })
}

/**
 * 高亮注解相关的文本
 * @param {string} nid 注解ID
 */
function highLightNote(nid) {
  const oldSelId = _status.selId, note = getNote(nid), $cellL = $('.cell-l')
  unwrapSelected($('.cell'), 'hi')
  if (note) {
    _status.selCls = 'hi'
    if ($cellL[0]) {
      selectPText($cellL, note.left)
      selectPText($('.cell-r'), note.right)
    } else {
      selectPText($('.cell'), note.left)
    }
    _status.selId = oldSelId
    delete _status.selCls
  }
}

/**
 * 遍历指定节点范围的所有文本节点，不改动DOM
 * @param {Node} startContainer 起始节点
 * @param {Node} endContainer 结束节点
 * @param {HTMLElement} cell 栏元素，用于避免出界
 * @param {Node[]} nodes 填充所有文本节点
 * @private
 */
function scanNodesToSel(startContainer, endContainer, cell, nodes) {
  const getRect = el => {
    const $e = $(el.closest ? el : el.parentElement), top = $e.offset().top
    return {top: top, bottom: top + $e.height()}
  }
  const endRc = getRect(endContainer)

  for (let el = startContainer; el && el !== cell; el = el && el.nextSibling) {
    if (!el || getRect(el).top > endRc.bottom) {
      break
    }
    el = el.firstChild || el
    const text = el.textContent.replace(/[\u3000\s]+/g, '').trim();
    if (el.parentElement && (text || nodes.length && el.parentElement.closest('p.text'))) {
      if ($(el.parentElement).closest('.note').length < 1) {
        nodes.push(el)
      }
    }
    if (el === endContainer) {
      break
    }
    while (el && !el.nextSibling && el !== endContainer && el !== cell) {
      el = el.parentElement
    }
  }
}

/**
 * 选择指定范围的文本
 * @param {HTMLElement[]} nodes 文本节点
 * @param {Node} startContainer 起始节点
 * @param {Node} endContainer 结束节点
 * @param {number} startOffset 起始节点中的起始偏移字符数
 * @param {number} endOffset 结束节点中的结束偏移字符数（不含此字符），-1则到末尾字符（含）
 * @param {Function|boolean} [replacer] 文本节点的内容替换函数，或true表示如果右侧是注解标签就扩大选择
 * @returns {number} 选择的节点数
 * @private
 */
function selNodes(nodes, startContainer, endContainer,
                   startOffset, endOffset, replacer=null) {
  let n = 0
  nodes.forEach(s => {
    const isSp = i => s.textContent[i] && (s.textContent[i] === '\u3000' || !s.textContent[i].trim())
    let i0 = s === startContainer ? startOffset : 0,
      i1 = s === endContainer && endOffset >= 0 ? endOffset : s.textContent.length;

    while (isSp(i0)) i0++
    while (i1 > 0 && isSp(i1)) i1--

    const text = i0 < i1 ? s.textContent.substring(i0, i1) : ''
    if (text) {
      const selCls = _status.selCls || 'selected'
      const span = $(`<span class="${selCls}" data-id="${_status.selId}"></span>`)
      const f = document.createDocumentFragment();

      if (i0 > 0) {
        f.append(document.createTextNode(s.textContent.substring(0, i0)))
      }
      f.append(span.text(text)[0])
      if (i1 < s.textContent.length) {
        f.append(document.createTextNode(s.textContent.substring(i1)))
      } else if (replacer === true && $(s.nextSibling).hasClass('note-tag')) {
        $(`<span class="${selCls}"></span>`).insertAfter(s.nextSibling)
      }
      if (typeof replacer === 'function') {
        replacer(text, s, f)
      } else {
        s.replaceWith(f)
      }
      n++
    }
  })
  return n
}

/**
 * 选择文本完成的后处理
 * @param {HTMLElement|jQuery} cell 栏元素
 * @param {number} n 点击或拉选操作中选择的节点数
 * @private
 */
function selNodesEnd(cell, n) {
  document.getSelection().empty()
  if (cell) {
    $('p.has-sel', cell).removeClass('has-sel all-sel')
    $('.cell .active').removeClass('active')
    if ($(cell).hasClass('cell-l')) { // 左栏仅保留当次选择
      $('.selected', cell).each((i, s) => {
        if (parseInt(s.dataset.id) !== _status.selId) {
          _unwrapNode(s)
        }
      })
    }
    _flatten($('p:has(.selected)', cell).get())
    _status.selId += n ? 1 : 0
  }
}

/**
 * @typedef {object} NoteSegment
 * @property {number} i0 在P段落中的起始位置，文本偏移量，包含此字符
 * @property {number} i1 在P段落中的结束位置，文本偏移量，不含此字符
 * @property {number} len 文本长度
 * @property {str} text 缩略文本，最多6字
 */
/**
 * @typedef {object} NoteRow
 * @property {number} i0 首片段在P段落中的起始位置，文本偏移量，包含此字符
 * @property {number} i1 末片段在P段落中的结束位置，文本偏移量，不含此字符
 * @property {number} len 文本累计长度
 * @property {number} line 内容区（卷）内的行号
 * @property {string} s_id 内容区（卷）ID
 * @property {number} [all] 是否选中了整段内容，1-全部，0-部分
 * @property {str} [text] 选中整段时的缩略文本，最多8字
 * @property {NoteSegment[]} [sel] 选中部分内容时的片段数组
 */

/**
 * @typedef {object} NoteBlock
 * @property {string} id 注解ID，在项目中唯一
 * @property {string} left_aid 被注解的经典ID
 * @property {string} [note_aid] 注解所用的经典ID
 * @property {NoteRow[]} left 被注解的段落内容，数组仅一个元素
 * @property {NoteRow[]} [right] 注解所用的段落内容
 * @property {number} [inline] 行间注(1)、段尾注(0)
 * @property {string} [type] 段前注 front
 * @property {object} [note] 预览发布时此对象代替right，结构为{text,source,tag}
 */

/**
 * 标记选中一段文本
 * @param {jQuery} $cell 栏元素
 * @param {NoteRow[]} rows 片段数据
 * @param {Function|boolean} [replacer] 文本节点的内容替换函数，或true表示如果右侧是注解标签就扩大选择
 */
function selectPText($cell, rows, replacer=null) {
  const inEdit = $cell.hasClass('cell-l') || $cell.hasClass('cell-r')
  rows.forEach(r => {
    const $p = $(`p.text[data-line='${r.line}'][data-s-id='${r.s_id}']`, $cell), p = $p[0]
    if (!p) {
      return !$cell[0] || !r.s_id || console.assert(p, r)
    }
    const nodes = []
    scanNodesToSel(p.firstChild, p.lastChild, inEdit ? $cell[0] : null, nodes)
    if (r.all) {
      selNodes(nodes, p.firstChild, p.lastChild, 0, -1, replacer)
    } else if (r.sel) {
      for (let i = 0, off = 0; i < r.sel.length; i++) {
        const s = r.sel[i], i0 = s.i0, i1 = s.i1
        for (let j = 0; j < nodes.length; j++) {
          const node = nodes[j], len = node.textContent.length
          if (off >= i1) {
            break
          }
          if (off + len > i0) {
            selNodes([node], node, node, i0 - off,
              Math.min(i1 - off, len), replacer)
          }
          off += len
        }
      }
    }
  })
  if (typeof replacer !== 'function') {
    selNodesEnd(inEdit ? $cell[0] : $cell, 0)
  }
}

function getNote(nid) {
  return nid && window.notes.filter(s => s.id === nid)[0]
}

/**
 * 插入注解元素
 * @param {NoteBlock} note 注解数据
 * @param $lf 左栏段落中的某个节点（只用其末项位置，不用其内容），在其后将插入注解标记上标元素
 * @param $rt 右栏选中的内容片段，将用其文本内容、标记被选用；或 {text,source,tag.code,name}
 * @param $rp 与$rt对应的各个段落，$rt为行间注数据时忽略此参数
 * @param [ignoreErr] 是否忽略错误
 */
function addNote(note, $lf, $rt, $rp, ignoreErr=false) {
  let $pos = $lf.last(), $next = $pos.next()
  const simple = typeof $rt.text === 'string', d = simple && $rt,
    oneCol = (nA['notes'] || []).filter(t => t.a_id === note.note_aid)[0], // 单栏释文经典
    tag = d ? d.tag || '注' : nA['note_tag'] || (oneCol && oneCol.tag)
  const $tag = $(`<sup class="note-tag" data-nid="${note.id}" data-tag="${tag}"></sup>`)
  let title = `〔${$tag.attr('data-tag')}〕`

  $tag.toggleClass('inline', note.inline === 1 && !note.type)
  if (note.inline && !note.type) { // 行间注
    const existInline = $next.closest(`.note-tag.inline[data-tag="${tag}"]`)[0]
    if (existInline) {
      return ignoreErr ? console.info(note) : showError('不能添加', '此处已有行间注，不能重复插入行间注。')
    }
    $tag.attr('data-text', (d ? d.text : $rt.map((i, s) => s.textContent).get().join('\u3000'))
      .replace(/[\s\n\u3000]+/g, '\u3000').replace(/[，。！？：；、\u3000]+$/, ''))
    title += $tag.attr('data-text')
    if (simple && d.source) {
      $tag.attr('data-source', d.source)
      title += '\n来源：' + d.source
    }
  } else {
    const $posP = $pos.closest('p')
    const $pNext = note.type === 'front' ? $posP.prev() : $posP.next()
    const $notes = $pNext.hasClass('note-p') ? $pNext : $(`<div class="note-p"><div class="close"/></div>`)
    const $pn_ = $notes.find(`.note-pn[data-pn="${_status.notePn}"]`)
    const $pn = $pn_[0] ? $pn_ : $(`<div class="note-pn" data-pn="${_status.notePn++}"/>`).appendTo($notes)
    const $item = $(`<div class="note-item" data-nid="${note.id}"/>`).appendTo($pn)
    let $text = $('<div/>')

    if (!$notes[0].parentElement) {
      if (!simple && !$rp[0]) {
        $tag.addClass('disabled')
      } else if (note.type === 'front') {
        $notes.insertBefore($posP)
      } else {
        $notes.insertAfter($posP)
      }
      $posP.addClass('has-note')
    }
    if (simple) {
      d.text.split('\n').forEach(s => {
        $text = $(`<div class="note-row note-text ellipsis-n"/>`).appendTo($item).text(s)
      })
    } else {
      $rp.each((i, p) => {
        $text = $(`<div class="note-row note-text ellipsis-n"/>`).appendTo($item)
          .text($('.selected', p).map((i, s) => {
            if (i < 10) title += s.textContent + '\n'
            return s.textContent
          }).get().join('\u3000'))
      })
    }
    title = ellipsisText(title + (d && d.text || ''), 100)

    const $head = $('.note-row', $pn).first()
    if (!$head.find('.note-row-head')[0]) {
      $(`<span class="note-row-head"/>`).prependTo($head)
        .attr('data-pn', $pn.attr('data-pn'))
    }
    $(`<span class="note-row-end"/>`).appendTo($text)
      .attr('data-tag', d && d.source || tag)
      .attr('title', (d && d.code || nA['code']) + ' ' + (d && d.name || nA['name']) + '\n点击隐藏')
    $tag.attr('data-pn', $pn.attr('data-pn'))
  }

  const $ins = $next.closest('.note-tag.inline')[0] ? $next : $pos
  const insTag = $ins.closest('.note-tag')[0] || $ins[0] && $ins[0].previousSibling
  $tag.attr('title', title).insertAfter($ins)
    .toggleClass('after', insTag ? insTag.tagName === 'SUP' : false)
  if ($rt.addClass) {
    $rt.addClass('used').removeClass('selected').attr('data-nid', note.id).removeAttr('data-id')
  }
}

/**
 * 注解数据渲染到页面
 * @param {NoteBlock[]} notes
 * @param {string} cellCls 被注解栏的类选择器，'-'则自适应相应的栏
 * @param {boolean} [fromReorder] reorderNoteTags 用
 */
function reloadNotes(notes, cellCls='.cell-l', fromReorder=false) {
  if (Array.isArray(notes)) {
    window.notes = notes
    $('.note-tag,.note-p').remove()
    unwrapSelected($('.cell'), 'hi')
    unwrapSelected($('.cell'), 'used')
    return setTimeout(() => reloadNotes(null, cellCls, fromReorder), 20)
  }
  buildNotes(cellCls)
  if (!fromReorder) {
    reorderNoteTags(cellCls)
  }
}

function buildNotes(cellCls='.cell-l') {
  _status.notePn = 1
  window.notes.forEach(note => {
    if (!note.left || !note.left_aid) return
    const cls = cellCls !== '-' ? cellCls : `.cell[data-id="${note.left_aid}"]`
    selectPText($(cls), note.left, true)
    if (note.right && !note.note) {
      selectPText($('.cell-r'), note.right)
    }

    const $lf = $(cls + ' .selected'), $rt = note.note || $('.cell-r .selected')
    addNote(note, $lf, $rt, $('.cell-r p:has(.selected)'), true)
    unwrapSelected($('.cell'))
  })
}

function reorderNoteTags(cellCls='.cell-l') {
  let pn = 0, changes = 0, notes2 = []
  $('.note-tag').each((i, tag) => {
    notes2.push(getNote(tag.dataset.nid))
    if (tag.dataset.pn && ++pn !== parseInt(tag.dataset.pn)) {
      changes++
    }
  })
  if (changes) {
    reloadNotes(notes2, cellCls, true)
  }
}
