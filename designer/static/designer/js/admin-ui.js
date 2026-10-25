(function(){
  'use strict';

  function featherIcons(){ if(window.feather){ try{ window.feather.replace(); }catch(e){} } }



  function setupThemeToggle(){
    var body=document.body;
    var toggle=document.getElementById('zvThemeToggle');
    if(!body||!toggle)return;
    var key='zenvibe-admin-theme';
    var saved='';
    try{saved=localStorage.getItem(key)||'';}catch(e){}
    if(saved==='dark')body.classList.add('zv-dark-admin');
    function syncIcon(){
      toggle.innerHTML=body.classList.contains('zv-dark-admin')?'<i data-feather="sun"></i>':'<i data-feather="moon"></i>';
      featherIcons();
    }
    syncIcon();
    toggle.addEventListener('click',function(){
      var dark=body.classList.toggle('zv-dark-admin');
      try{localStorage.setItem(key,dark?'dark':'light');}catch(e){}
      syncIcon();
    });
  }
  function setupSidebar() {
    var body = document.body;
    var sidebar = document.getElementById('zvSidebar');
    var toggle = document.getElementById('zvSidebarToggle');

    if (!sidebar || !toggle) return;

    var key = 'zenvibe-sidebar-collapsed';

    function isDesktop() {
        return window.innerWidth > 991;
    }

    function setDesktopCollapsed(collapsed) {
        body.classList.toggle('zv-sidebar-collapsed', collapsed);
        sidebar.classList.toggle('zv-sidebar-collapsed', collapsed);

        try {
            localStorage.setItem(key, collapsed ? '1' : '0');
        } catch (e) {}
    }

    /* Restore state */
    if (isDesktop()) {
        var collapsed = false;

        try {
            collapsed = localStorage.getItem(key) === '1';
        } catch (e) {}

        setDesktopCollapsed(collapsed);
    }

    /* Main hamburger */
    toggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        if (isDesktop()) {
            var collapsed =
                !body.classList.contains('zv-sidebar-collapsed');

            setDesktopCollapsed(collapsed);
        } else {
            sidebar.classList.toggle('open');
        }
    });

    /* Submenus */
    document
        .querySelectorAll(
            '.zv-sidebar .sidebar-menu > li > .sidebar-header'
        )
        .forEach(function(a) {

            var li = a.parentElement;
            var sub = li.querySelector('.sidebar-submenu');

            if (!sub) return;

            a.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                var opening =
                    !li.classList.contains('zv-menu-open');

                document
                    .querySelectorAll(
                        '.zv-sidebar .sidebar-menu > li.zv-menu-open'
                    )
                    .forEach(function(other) {
                        if (other !== li) {
                            other.classList.remove('zv-menu-open');
                        }
                    });

                li.classList.toggle('zv-menu-open', opening);
            });
        });

    /* Active menu: select the most specific matching URL, not /admin/ on every page. */
    var path = window.location.pathname;
    var currentParams = new URLSearchParams(window.location.search);
    var currentPage = currentParams.get('page__exact') || currentParams.get('page');
    var links = Array.prototype.slice.call(document.querySelectorAll('.zv-sidebar a[href]'));
    var best = null;
    var bestLength = -1;
    links.forEach(function(a) {
        var raw = a.getAttribute('href');
        if (!raw || raw === '/' || raw.indexOf('javascript:') === 0 || raw.charAt(0) === '#') return;
        var url;
        try { url = new URL(raw, window.location.href); } catch (e) { return; }
        if (url.origin !== window.location.origin) return;
        var target = url.pathname;
        if (target !== path && (target === '/admin/' || path.indexOf(target) !== 0)) return;
        var targetPage = url.searchParams.get('page__exact');
        if (targetPage && targetPage !== currentPage) return;
        var score = target.length + (targetPage ? 1000 : 0);
        if (score > bestLength) { best = a; bestLength = score; }
    });
    document.querySelectorAll('.zv-sidebar .active').forEach(function(el) {
        el.classList.remove('active');
    });
    if (best) {
        var selected = best.closest('li');
        if (selected) selected.classList.add('active');
        var group = best.closest('.sidebar-menu > li');
        if (group) {
            group.classList.add('active');
            if (group !== selected) group.classList.add('zv-menu-open');
        }
    }

    /* Keep the selected menu visible in the independently scrolling sidebar.
       This must not move the page body or browser viewport. */
    var scrollArea = sidebar.querySelector('.sidebar-menu') || sidebar;
    var selectedLink = best;
    if (!selectedLink && path.indexOf('/admin/designer/orderworkflowconfig/') === 0) {
        selectedLink = sidebar.querySelector('a[href*="/admin/designer/paymentsetup/"]');
        if (selectedLink) {
            var fallbackItem = selectedLink.closest('li');
            if (fallbackItem) fallbackItem.classList.add('active');
        }
    }
    if (selectedLink) {
        var activeItem = selectedLink.closest('li');
        if (activeItem) {
            var target = activeItem.closest('.sidebar-menu > li') || activeItem;
            function revealSelectedMenu() {
                var scrollable = target.parentElement;
                while (scrollable && scrollable !== document.body) {
                    var style = window.getComputedStyle(scrollable);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                        scrollable.scrollHeight > scrollable.clientHeight) break;
                    scrollable = scrollable.parentElement;
                }
                if (!scrollable || scrollable === document.body) scrollable = sidebar;
                var menuRect = target.getBoundingClientRect();
                var boxRect = scrollable.getBoundingClientRect();
                if (menuRect.top < boxRect.top + 12 || menuRect.bottom > boxRect.bottom - 12) {
                    scrollable.scrollTop += menuRect.top - boxRect.top -
                        Math.max(12, (boxRect.height - menuRect.height) / 2);
                }
            }
            window.requestAnimationFrame(revealSelectedMenu);
        }
    }

    /* Mobile outside click */
    document.addEventListener('click', function(e) {
        if (
            !isDesktop() &&
            sidebar.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            !toggle.contains(e.target)
        ) {
            sidebar.classList.remove('open');
        }
    });

    /* Responsive switching */
    window.addEventListener('resize', function() {

        if (isDesktop()) {
            sidebar.classList.remove('open');

            var collapsed = false;

            try {
                collapsed = localStorage.getItem(key) === '1';
            } catch (e) {}

            setDesktopCollapsed(collapsed);

        } else {
            body.classList.remove('zv-sidebar-collapsed');
            sidebar.classList.remove('zv-sidebar-collapsed');
        }
    });
}

  function setupGlobalSearch(){
    var search=document.getElementById('zvAdminSearch');
    if(!search)return;
    search.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();var q=search.value.trim();if(q)location.href='/admin/designer/product/?q='+encodeURIComponent(q);}});
  }

  function setupFilters(){
    var nativeFilter=document.getElementById('changelist-filter');
    var toolbar=document.getElementById('toolbar');
    if(!nativeFilter||!toolbar||document.querySelector('.zv-filter-control'))return;

    var groups=[];
    var headings=Array.prototype.slice.call(nativeFilter.querySelectorAll('h3'));
    headings.forEach(function(h){
      var list=h.nextElementSibling;
      if(!list || list.tagName!=='UL')return;
      var options=[];
      Array.prototype.slice.call(list.querySelectorAll('li a')).forEach(function(a){
        options.push({label:(a.textContent||'').trim(),url:a.href,selected:!!(a.parentElement&&a.parentElement.classList.contains('selected'))});
      });
      if(options.length)groups.push({label:(h.textContent||'Filter').replace(/^\s*[↓↑]\s*/,'').trim(),options:options});
    });
    if(!groups.length)return;

    var control=document.createElement('div');control.className='zv-filter-control';
    var button=document.createElement('button');button.type='button';button.className='zv-filter-dropdown-button';button.textContent='Filters';button.setAttribute('aria-expanded','false');
    var panel=document.createElement('div');panel.className='zv-filter-dropdown-panel';
    var grid=document.createElement('div');grid.className='zv-filter-grid';

    groups.forEach(function(group,index){
      var field=document.createElement('div');field.className='zv-filter-field-v79';
      var label=document.createElement('label');label.htmlFor='zv-v79-filter-'+index;label.textContent=group.label;
      var select=document.createElement('select');select.id='zv-v79-filter-'+index;
      group.options.forEach(function(item){var option=document.createElement('option');option.value=item.url;option.textContent=item.label||'All';option.selected=item.selected;select.appendChild(option);});
      select.addEventListener('change',function(){if(this.value)window.location.assign(this.value);});
      field.appendChild(label);field.appendChild(select);grid.appendChild(field);
    });

    var footer=document.createElement('div');footer.className='zv-filter-footer';
    var clear=document.createElement('a');clear.className='zv-filter-clear-v79';clear.textContent='Clear filters';
    var params=new URLSearchParams(window.location.search);var q=params.get('q');clear.href=window.location.pathname+(q?'?q='+encodeURIComponent(q):'');footer.appendChild(clear);
    panel.appendChild(grid);panel.appendChild(footer);control.appendChild(button);control.appendChild(panel);toolbar.appendChild(control);

    button.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();var open=control.classList.toggle('zv-filter-open');button.setAttribute('aria-expanded',open?'true':'false');});
    panel.addEventListener('click',function(e){e.stopPropagation();});
    document.addEventListener('click',function(){control.classList.remove('zv-filter-open');button.setAttribute('aria-expanded','false');});
  }

  function setupChart(){
    var el=document.getElementById('zvPerformanceChart'), metric=document.getElementById('zvChartMetric'), group=document.getElementById('zvChartGroup'), dataNode=document.getElementById('zv-chart-data');
    if(!el||!metric||!group||!dataNode)return;
    var rows=[];try{rows=JSON.parse(dataNode.textContent||'[]')}catch(e){}
    function money(v){return '$'+Number(v||0).toFixed(2)}
    function labelFor(row,key){if(key==='month')return row.month||'Unknown';if(key==='status')return row.status_label||'Unknown';if(key==='payment')return row.payment_label||'Unknown';if(key==='category')return row.category||'Uncategorised';return 'All';}
    function render(){
      var m=metric.value,g=group.value,buckets={};
      rows.forEach(function(r){var k=labelFor(r,g);if(!buckets[k])buckets[k]=0;if(m==='orders')buckets[k]+=1;else if(m==='revenue')buckets[k]+=Number(r.total||0);else buckets[k]+=Number(r.quantity||0);});
      var items=Object.keys(buckets).map(function(k){return[k,buckets[k]]});
      if(g==='month')items.sort(function(a,b){return a[0].localeCompare(b[0]);});else items.sort(function(a,b){return b[1]-a[1];});
      el.innerHTML='';if(!items.length){el.innerHTML='<div class="zv-chart-empty">No order data available for this chart.</div>';return;}
      var max=Math.max.apply(null,items.map(function(x){return x[1]}))||1;
      items.forEach(function(item){var col=document.createElement('div');col.className='zv-chart-column';var val=document.createElement('div');val.className='zv-chart-value';val.textContent=m==='revenue'?money(item[1]):String(item[1]);var wrap=document.createElement('div');wrap.className='zv-chart-bar-wrap';var bar=document.createElement('i');bar.className='zv-chart-bar';bar.style.height=Math.max(3,(item[1]/max)*100)+'%';bar.title=item[0]+': '+val.textContent;wrap.appendChild(bar);var lab=document.createElement('div');lab.className='zv-chart-label';lab.textContent=item[0];lab.title=item[0];col.appendChild(val);col.appendChild(wrap);col.appendChild(lab);el.appendChild(col);});
    }
    metric.addEventListener('change',render);group.addEventListener('change',render);render();
  }

  function init(){featherIcons();setupThemeToggle();setupSidebar();setupGlobalSearch();setupChart();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
