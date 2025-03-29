let _$tree = {}, _curNode = null

function _scanTocRows(ext, rows) {
  const scan = (items, level, from, end) => {
    let linked = 0, lv1 = level
    while (!items.length && lv1 < 13 && from < end) {
      for (let i = from; i < end; i++) { // 在段落中找当前层级的，没有则找更深层级
        const r = rows[i]
        if ((!items.length && r.level > lv1) || r.level === lv1) {
          r.level = lv1
          linked += r.s_id ? 1 : 0
          items.push({
            id: 'toc-' + r.id, text: r.text, icon: r.s_id ? 'linked' : '',
            data: {i: i, ext: ext, level: lv1, id: r.id, s_id: r.s_id, line: r.line}
          })
        }
      }
    }
    for (let i = 0; i < items.length; i++) { // 对找到的每项，递归查找子节点
      const children = [], item = items[i]
      const subLinked = scan(children, level + 1, item.data.i + 1,
        items[i+1] ? items[i+1].data.i : end)

      if (subLinked) {
        linked += subLinked
        item.state = {opened: true}
      }
      if (children.length) {
        item.children = children
      }
    }
    return linked
  }

  const items = []
  scan(items, 1, 0, rows && rows.length)
  return items
}

function _tocLoaded(d, ext, a_id, ti, ended) {
  const items = _scanTocRows(ext, d.rows)
  const tocSel = `#toc-tree${ext}`, tree = $.jstree.reference(tocSel + '>div')
  if (tree) tree.destroy()
  _curNode = null
  const $w = _$tree[ext] = $(tocSel), $t = $(tocSel + '>div')
  $w.attr('data-a-id', a_id).attr('data-toc-i', ti)
  $t.jstree({core: {data: items, animation: 0}})
  $(`.toc-tree-p[data-ext="${ext}"] .drop-toc-name`).text(d.name)

  $t.on('loaded.jstree', () => _initTocTree(ended))
    .on('changed.jstree', _tocNodeChanged)
}

function tocLoad(ext, a_id, ti, ended=null) {
  if (window.all_toc) {
    const r = all_toc.filter(a => a.a_id === a_id && parseInt(ti) === a.toc_i)[0]
    return r && _tocLoaded(r, ext, a_id, ti, ended)
  }
  getApi(`/proj/toc/${a_id}/${ti}`,
      r => _tocLoaded(r.data, ext, a_id, ti, ended), $.noop)
}

function _initTocTree(ended) {
  $('.jstree-anchor').each((i, a) => a.removeAttribute('href'))
  $('.jstree-icon.jstree-themeicon-custom').removeClass('jstree-themeicon-custom')
  ended && ended()
}

function _tocNodeChanged(e, data) {
  _curNode=data.node
  navigateToPara(data.node)
}

function _findTocPara(texts, pElem) {
  const py = pElem.getBoundingClientRect().top
  texts.sort((a, b) => a.getBoundingClientRect().top < b.getBoundingClientRect().top)
  for (let i = texts.length - 1; i >= 0; i--) {
    if (texts[i].getBoundingClientRect().top < py) {
      return texts[i]
    }
  }
}

function _isSameToc(obj, ext) {
  const $t = _$tree[ext], oldId = $t.attr('data-a-id'), oldTi = $t.attr('data-toc-i')
  return oldId === obj.a_id && oldTi + '' === obj.toc_i + ''
}

function _setActiveToc(ext) {
  $('.active-toc').removeClass('active-toc')
  $(`.toc-tree-p[data-ext="${ext}"]`).addClass('active-toc')
}

function tocEnsureVisible(p, reload=false) {
  if (p && !p.ext) {
    p.ext = _getTocExt(p)
    if (!p.ext) {
      p.ext = $('.toc-tree-p:not(.active-toc):visible').data('ext')
      p.ext = p.ext || '1'
    }
  }
  if (!p || !_$tree[p.ext]) {
    return
  }
  if (p.a_id && p.s_id && p.line) { // 科判条目 或 段落
    clearTimeout(window._tocTm)
    delete window._tocTm
    if (!p.toc_id && p.element) { // 是未关联科判条目的段落：往上找关联的，本栏无科判则可横向找
      window._tocTm = setTimeout(function () {
        // 取红线下的tr对应栏的单元格，及栏的科判数
        const $c = $(`tr>[data-i="${p.a_i}"][data-toc-i]`), colTocI = $c.data('toc-i')
        // 先在此单元格内向上找已关联的段落
        let tocP = _findTocPara($(`[data-row-i="${p.row_i || 0}"] > [data-i="${p.a_i}"] > [data-toc-id]`).get(), p.element)
        if (colTocI !== '') { // 此栏有科判
          // 在此栏内往上找关联的，找不到就仅切换科判树
          tocP = tocP || _findTocPara($(`tr>[data-i="${p.a_i}"] > [data-toc-id]`).get(), p.element)
          tocP = tocP || {toc_i: parseInt(colTocI), a_id: $c.data('id'), toc_id: '-'}
        } else { // 此栏无科判，就先在当前tr其他单元格找，没有就往上找任意关联项
          tocP = tocP || _findTocPara($(`[data-row-i="${p.row_i}"] [data-toc-id]`).get(), p.element)
          tocP = tocP || _findTocPara($(`[data-toc-id]`).get(), p.element)
        }
        p = tocP && (tocP.a_id ? tocP : getParaInfo($(tocP)))
        tocEnsureVisible(p && p.toc_id ? p : {})
      }, 20)
      return
    }
  }

  if (p.toc_id && !p.loaded) {
    p.loaded = true
    if (reload === true) { // 科判内容改变
      return tocLoad(p.ext, p.a_id, p.toc_i, () => tocEnsureVisible(p, 1))
    }
    if (!reload && p.toc_i !== undefined && p.toc_id === '-') { // 此栏有科判但未关联到段落
      if (!_isSameToc(p, p.ext)) {
        return tocLoad(p.ext, p.a_id, p.toc_i, () => _setActiveToc(p.ext)) // 仅切换科判树
      }
    }
    else if (!reload && $(`.cell[data-id="${p.a_id}"] [data-toc-i="${p.toc_i}"][data-toc-id="${p.toc_id}"]`)[0]) {
      if (!_isSameToc(p, p.ext)) {
        return tocLoad(p.ext, p.a_id, p.toc_i, () => tocEnsureVisible(p))
      }
    }
  }

  const tree = $.jstree.reference(`#toc-tree${p.ext}>div`)
  const node = getTocNode(p.toc_id, p.ext) || getTocNode(p['next_id'], p.ext)

  _setActiveToc(p.ext)
  if (node) {
    tree.deselect_all(true)
    if (node.parents) {
      // tree.close_all()
      for (const p of node.parents) {
        tree.open_node(p)
      }
    }
    tree.open_node(p.toc_id)
    if (!p['next_id']) {
      tree.select_node(node.id, !reload)
    }
    scrollTreeNodeToVisible(tree, node)
  }
}

function scrollToVisible(scrollOwner, $prev, $next) {
  const $s = $(scrollOwner), sr = $s.offset(),
    gap = $s.height() < 150 ? 20 : 80,
    rPrev = $prev && $prev.offset(),
    rNext = $next && $next.offset()

  if (sr && rPrev && rPrev.top < sr.top + gap) {
    scrollOwner.scrollTop -= sr.top + gap - rPrev.top
  }
  if (sr && rNext && rNext.top + gap > sr.top + scrollOwner.clientHeight) {
    scrollOwner.scrollTop += rNext.top - sr.top + gap - scrollOwner.clientHeight
  }
  if (sr && rPrev) {
    if (rPrev.left < sr.left + 4) {
      scrollOwner.scrollLeft -= sr.left + 4 - rPrev.left
    }
    if (rPrev.left + $prev.width() + 4 > sr.left + scrollOwner.clientWidth) {
      scrollOwner.scrollLeft += rPrev.left + $prev.width() + 4 - sr.left - scrollOwner.clientWidth
    }
  }
}

function scrollTreeNodeToVisible(tree, node) {
  const $prev = tree.get_prev_dom(node), $next = tree.get_next_dom(node)
  scrollToVisible($next && $next.closest('.toc-tree')[0], $prev, $next)
}

function scrollParaToVisible($p) {
  const owner = $p.closest('.autoscroll')[0] || document.querySelector('.columns-p')
  scrollToVisible(owner, $p, $p)
}

function _getTocExt(p) {
  const $t = $(`.toc-tree[data-a-id="${p.a_id}"][data-toc-i="${p.toc_i}"]:visible`)
  return $t.closest('[data-ext]').data('ext')
}

function _extendNode(node) {
  if (node) {
    const $t = _$tree[node.data.ext]
    const data = Object.assign({a_id: $t.attr('data-a-id'), toc_i: $t.attr('data-toc-i'),
       text: node.text, toc_id: node.data.id}, node.data)
    return Object.assign({}, node, {data: data})
  }
}

function getCurrentTocNode() {
  return _extendNode(_curNode) || {}
}

function getTocNode(toc_id, ext) {
  if (ext && ext.a_id) {
    ext = _getTocExt(ext)
  }
  const tree = $.jstree.reference(`#toc-tree${ext}>div`)
  return toc_id && tree && tree.get_node(('toc-' + (toc_id + '').split('-').slice(-1)))
}

/**
 * 根据树节点或节点ID得到节点信息、文中关联项
 * @param {jQuery|string} $a 树节点对象或节点ID
 * @param {string} ext 树序号，'1'、'2'
 * @returns {Array} [NodeInfo, $toc_row, ext]
 */
function getTocRowByTreeNode($a, ext) {
  const id = !$a || typeof $a === 'string' ? $a : $a.closest('li').attr('id')
  const node = getTocNode(id, ext), ret = [_extendNode(node)]

  if (node) {
    const $t = _$tree[ext], a_id = $t.attr('data-a-id'), ti = $t.attr('data-toc-i')
    const tid = id.replace('toc-', '') // tree id to toc id
    ret[1] = $(`.cell[data-id="${a_id}"] .toc_row[data-toc-i="${ti}"][data-toc-id="${tid}"]`)
    ret[2] = ext
  }
  return ret
}

function _findTocRowByNode(node, traverse=true) {
  const ext = node && node.data.ext
  const r = getTocRowByTreeNode(node && node.id || '', ext)
  const $toc_row = node && r[1]

  if (node && !$toc_row[0] && traverse) {
    const scan = id => {
      const node = getTocNode(id, ext), r1 = getTocRowByTreeNode(node.id, ext)
      if (r1[1][0]) {
        return r1
      }
      for (let i = 0; i < node.children.length; i++) {
        const r2 = scan(node.children[i])
        if (r2) {
          return r2
        }
      }
    }
    return scan(node.id)
  }
  return r
}

function navigateToPara(node) {
  const r = _findTocRowByNode(node)
  if (node) {
    _setActiveToc(node.data.ext)
  }
  if (r && r[1]) {
    window.activatePara(r[1])
    scrollParaToVisible(r[1])
  }
}

$(function () {
  $(document).on('click', '.toc-dropdown li', e => {
    const $li = $(e.target).closest('li')
    const ext = $li.closest('[data-ext]').data('ext')
    tocLoad(ext, $li.data('a-id'), $li.data('toc-i'))
    _setActiveToc(ext)
  })
  .on('click', '.toc-tree', e => {
    if (!e.target.closest('ul')) {
      const $t = $(e.target.closest('.toc-tree>div')), tree = $.jstree.reference($t)
      if (tree) {
        tree.deselect_all()
        _setActiveToc($t.closest('[data-ext]').data('ext'))
      }
    }
  })
})
