/* ==========================================================================
   ZenVibe — sitewide media path fallback
   ==========================================================================
   Some hosting setups (cPanel/Passenger deployments in particular) serve
   STATIC_URL/MEDIA_URL under a different path prefix than what settings.py
   declares (e.g. "/media/..." instead of the configured "/zenvibe/media/...").
   The Awards, Bags, Drinkware and generic photo customizers already retry
   several candidate URLs server-side for their own canvases. This script
   gives the SAME protection to every ordinary <img> on the site — category
   tiles, product grid photos, the choose-design hero image, and so on —
   without needing to touch every template individually.

   How it works: <img error> events don't bubble, but they DO fire during the
   capture phase, so a single window-level listener with {capture:true} sees
   every failed image on the page, including ones added dynamically later.
   On failure, we try the same URL with the "/zenvibe" prefix toggled
   (added if missing, stripped if present), then give up after that.
   Each <img> is only retried once, tracked via a WeakSet, so a genuinely
   missing file just falls back to the browser's normal broken-image state
   instead of looping.
   ========================================================================== */
(function(){
  'use strict';
  var retried = new WeakSet();

  function altUrl(src){
    try{
      var u = new URL(src, window.location.href);
      if(u.origin !== window.location.origin) return null; // never touch cross-origin images
      if(u.pathname.startsWith('/zenvibe/')){
        u.pathname = u.pathname.slice('/zenvibe'.length);
      } else if(u.pathname.startsWith('/static/') || u.pathname.startsWith('/media/')){
        u.pathname = '/zenvibe' + u.pathname;
      } else {
        return null; // not a recognisable static/media asset path — leave it alone
      }
      return u.pathname + u.search + u.hash;
    }catch(e){
      return null;
    }
  }

  window.addEventListener('error', function(e){
    var img = e.target;
    if(!img || img.tagName !== 'IMG') return;
    if(retried.has(img)) return;
    var next = altUrl(img.currentSrc || img.src);
    if(!next) return;
    retried.add(img);
    img.src = next;
  }, true);
})();
