(() => {
  const slides=[...document.querySelectorAll('.slide')];
  let current=0;
  const previous=document.getElementById('previous'), next=document.getElementById('next');
  const read=document.getElementById('reading');
  function resize() { document.documentElement.style.setProperty('--scale',Math.min(innerWidth/1600,innerHeight/900)); }
  function go(index) {
    current=Math.max(0,Math.min(slides.length-1,index));
    slides[current].scrollIntoView({behavior:'instant',block:'start'});
    history.replaceState(null,'','#'+slides[current].id);
    previous.disabled=current===0; next.disabled=current===slides.length-1;
  }
  previous.addEventListener('click',()=>go(current-1));next.addEventListener('click',()=>go(current+1));
  read.addEventListener('click',()=>{
    const enabled=document.body.classList.toggle('read-mode');
    document.documentElement.style.scrollSnapType=enabled?'none':'y mandatory';
    read.setAttribute('aria-pressed',String(enabled));
    read.textContent=enabled?'▣':'Aa';
  });
  addEventListener('keydown',event=>{
    if(event.target.closest('button,a,input,textarea')||event.ctrlKey||event.metaKey||event.altKey)return;
    if(['ArrowRight','PageDown',' '].includes(event.key)){event.preventDefault();go(current+1);}
    if(['ArrowLeft','PageUp'].includes(event.key)){event.preventDefault();go(current-1);}
    if(event.key==='Home'){event.preventDefault();go(0);}
    if(event.key==='End'){event.preventDefault();go(slides.length-1);}
  });
  const observer=new IntersectionObserver(entries=>{
    entries.forEach(entry=>{if(entry.intersectionRatio>.55){current=slides.indexOf(entry.target);previous.disabled=current===0;next.disabled=current===slides.length-1;}});
  },{threshold:.55});slides.forEach(slide=>observer.observe(slide));
  resize();addEventListener('resize',resize);
  const hash=decodeURIComponent(location.hash.slice(1));
  const start=slides.findIndex(s=>s.id===hash);if(start>=0)go(start);
  Promise.all([document.fonts.ready,...[...document.images].map(i=>i.decode().catch(()=>{}))]).then(()=>{window.__consultingReady=true;});
})();
