(() => {
  const slides = [...document.querySelectorAll('.slide')];
  let current = 0;
  const resize = () => document.documentElement.style.setProperty('--scale', Math.min(innerWidth / 1600, innerHeight / 900));
  function go(index) {
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides[current].scrollIntoView({behavior: 'instant', block: 'start'});
    history.replaceState(null, '', '#' + slides[current].id);
  }
  function reading(enabled) {
    document.body.classList.toggle('read-mode', enabled);
    document.documentElement.style.scrollSnapType = enabled ? 'none' : 'y mandatory';
  }
  addEventListener('keydown', event => {
    if (event.target.closest('button,a,input,textarea,select') || event.ctrlKey || event.metaKey || event.altKey) return;
    if (['ArrowRight', 'PageDown', ' '].includes(event.key)) { event.preventDefault(); go(current + 1); }
    if (['ArrowLeft', 'PageUp'].includes(event.key)) { event.preventDefault(); go(current - 1); }
    if (event.key === 'Home') { event.preventDefault(); go(0); }
    if (event.key === 'End') { event.preventDefault(); go(slides.length - 1); }
    if (event.key.toLowerCase() === 'r') { event.preventDefault(); reading(!document.body.classList.contains('read-mode')); }
  });
  let start = null;
  addEventListener('touchstart', event => {
    start = event.touches.length === 1 && !event.target.closest('a,button,input,textarea') ? {x:event.touches[0].clientX,y:event.touches[0].clientY} : null;
  }, {passive:true});
  addEventListener('touchend', event => {
    if (!start || document.body.classList.contains('read-mode')) return;
    const dx = event.changedTouches[0].clientX - start.x, dy = event.changedTouches[0].clientY - start.y;
    start = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.4) go(current + (dx < 0 ? 1 : -1));
  }, {passive:true});
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => { if (entry.intersectionRatio > .55) current = slides.indexOf(entry.target); });
  }, {threshold:.55});
  slides.forEach(slide => observer.observe(slide));
  resize(); addEventListener('resize', resize);
  reading(innerWidth < 650);
  const index = slides.findIndex(slide => slide.id === decodeURIComponent(location.hash.slice(1)));
  if (index >= 0) go(index);
  Promise.all([document.fonts.ready, ...[...document.images].map(image => image.decode().catch(() => {}))]).then(() => { window.__consultingReady = true; });
})();
